//! MIT photo scanner. Links `czkawka_core` only (MIT). Does not link `krokiet` (GPL-3.0-only).
//! Never deletes, trashes, or renames the photos it scans. Organize quarantines files later.

use std::collections::HashMap;
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::{Duration, UNIX_EPOCH};

use czkawka_core::common::model::{CheckingMethod, HashType};
use czkawka_core::common::progress_data::ProgressData;
use czkawka_core::common::tool_data::{CommonData, DeleteMethod};
use czkawka_core::common::traits::Search;
use czkawka_core::re_exported::{FilterType, HashAlg};
use czkawka_core::tools::duplicate::{DuplicateFinder, DuplicateFinderParameters};
use czkawka_core::tools::similar_images::{
    GeometricInvariance, SimilarImages, SimilarImagesParameters,
};
use serde::{Deserialize, Serialize};

const PHOTO_EXTENSIONS: &[&str] = &[
    "jpg", "jpeg", "png", "gif", "webp", "heic", "heif", "tif", "tiff", "bmp",
];

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Request {
    directories: Vec<PathBuf>,
    #[serde(default = "default_true")]
    recursive: bool,
    #[serde(default = "default_true")]
    exact: bool,
    #[serde(default = "default_true")]
    similar: bool,
    #[serde(default)]
    minimum_bytes: u64,
    #[serde(default = "default_difference")]
    max_difference: u32,
    #[serde(default = "default_hash_size")]
    hash_size: u8,
    #[serde(default = "default_hash_alg")]
    hash_alg: String,
    #[serde(default = "default_invariance")]
    geometric_invariance: String,
    preview_dir: PathBuf,
    #[serde(default)]
    extensions: Vec<String>,
    #[serde(default)]
    stop_file: Option<PathBuf>,
}

fn default_true() -> bool {
    true
}
fn default_difference() -> u32 {
    5
}
fn default_hash_size() -> u8 {
    16
}
fn default_hash_alg() -> String {
    "Gradient".into()
}
fn default_invariance() -> String {
    "mirror-flip-rotate90".into()
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct PhotoFile {
    path: String,
    size: u64,
    width: u32,
    height: u32,
    modified: u64,
    difference: u32,
    preview_path: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct PhotoGroup {
    files: Vec<PhotoFile>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct ScanOutput {
    stopped: bool,
    heic_decoder: String,
    warnings: Vec<String>,
    exact: Vec<PhotoGroup>,
    similar: Vec<PhotoGroup>,
}

struct Preview {
    preview_path: PathBuf,
    width: u32,
    height: u32,
}

fn main() {
    let mut args = std::env::args().skip(1);
    match args.next().as_deref() {
        Some("--version") => {
            println!("similar-photos {}", env!("CARGO_PKG_VERSION"));
            println!("czkawka_core {}", czkawka_core::CZKAWKA_VERSION);
        }
        Some("--request") => {
            let path = args.next().unwrap_or_default();
            if let Err(error) = run_request(Path::new(&path)) {
                emit(&serde_json::json!({"type": "error", "message": error}));
                std::process::exit(1);
            }
        }
        _ => {
            eprintln!("usage: similar-photos --request <request.json>");
            std::process::exit(2);
        }
    }
}

fn run_request(path: &Path) -> Result<(), String> {
    let raw = fs::read_to_string(path).map_err(|error| format!("cannot read request: {error}"))?;
    let request: Request = serde_json::from_str(&raw).map_err(|error| format!("invalid request: {error}"))?;
    let output = scan(&request, |event| emit(&event))?;
    emit(&serde_json::json!({
        "type": "result",
        "stopped": output.stopped,
        "heicDecoder": output.heic_decoder,
        "warnings": output.warnings,
        "exact": output.exact,
        "similar": output.similar,
    }));
    Ok(())
}

fn emit(value: &impl Serialize) {
    let mut stdout = io::stdout().lock();
    if let Ok(line) = serde_json::to_string(value) {
        let _ = writeln!(stdout, "{line}");
        let _ = stdout.flush();
    }
}

fn scan(request: &Request, mut progress: impl FnMut(serde_json::Value)) -> Result<ScanOutput, String> {
    if request.directories.is_empty() {
        return Err("at least one directory is required".into());
    }
    if !request.exact && !request.similar {
        return Err("exact and similar cannot both be off".into());
    }
    if ![8, 16, 32, 64].contains(&request.hash_size) {
        return Err("hashSize must be 8, 16, 32, or 64".into());
    }
    let hash_alg = parse_hash_alg(&request.hash_alg)?;
    let invariance = parse_invariance(&request.geometric_invariance)?;
    let extensions = allowed_extensions(request);
    fs::create_dir_all(&request.preview_dir).map_err(|error| format!("cannot create preview dir: {error}"))?;

    let stop = Arc::new(AtomicBool::new(false));
    watch_stop_file(request.stop_file.clone(), Arc::clone(&stop));

    let mut warnings = Vec::new();
    let heic_decoder = heic_decoder_name();
    let photos = collect_photos(request, &extensions, &stop, &mut progress, &mut warnings)?;
    let heic_count = photos.iter().filter(|path| is_heic(path)).count();
    if heic_count > 0 && heic_decoder == "none" {
        warnings.push("HEIC_DECODE_UNAVAILABLE".into());
    }

    let (staged_names, previews) = stage_previews(
        &photos,
        &request.preview_dir,
        &stop,
        &mut progress,
        &mut warnings,
    )?;

    let mut stopped = stop.load(Ordering::Relaxed);
    let mut exact = Vec::new();
    if request.exact && !stopped {
        progress(progress_event("exact", 0, photos.len(), "正在比对完整内容"));
        exact = find_exact(request, &extensions, &stop, &previews)?;
        stopped = stop.load(Ordering::Relaxed);
    }
    let mut similar = Vec::new();
    if request.similar && !stopped {
        progress(progress_event("similar", 0, photos.len(), "正在计算感知哈希"));
        similar = find_similar(request, hash_alg, invariance, &staged_names, &previews, &stop)?;
        stopped = stop.load(Ordering::Relaxed) || stopped;
    }

    Ok(ScanOutput {
        stopped,
        heic_decoder: heic_decoder.into(),
        warnings,
        exact,
        similar,
    })
}

fn progress_event(stage: &str, checked: usize, total: usize, label: &str) -> serde_json::Value {
    serde_json::json!({
        "type": "progress",
        "stage": stage,
        "checked": checked,
        "total": total,
        "label": label,
    })
}

fn watch_stop_file(path: Option<PathBuf>, stop: Arc<AtomicBool>) {
    let Some(path) = path else { return };
    thread::spawn(move || {
        while !stop.load(Ordering::Relaxed) {
            if path.is_file() {
                stop.store(true, Ordering::Relaxed);
                break;
            }
            thread::sleep(Duration::from_millis(150));
        }
    });
}

fn allowed_extensions(request: &Request) -> Vec<String> {
    let source = if request.extensions.is_empty() {
        PHOTO_EXTENSIONS.iter().map(|ext| (*ext).to_string()).collect()
    } else {
        request.extensions.clone()
    };
    source
        .into_iter()
        .map(|ext| ext.trim().trim_start_matches('.').to_ascii_lowercase())
        .filter(|ext| !ext.is_empty())
        .collect()
}

fn parse_hash_alg(value: &str) -> Result<HashAlg, String> {
    match value.to_ascii_lowercase().as_str() {
        "mean" => Ok(HashAlg::Mean),
        "gradient" => Ok(HashAlg::Gradient),
        "blockhash" => Ok(HashAlg::Blockhash),
        "vertgradient" => Ok(HashAlg::VertGradient),
        "doublegradient" => Ok(HashAlg::DoubleGradient),
        "median" => Ok(HashAlg::Median),
        _ => Err(format!("unsupported hashAlg: {value}")),
    }
}

fn parse_invariance(value: &str) -> Result<GeometricInvariance, String> {
    match value {
        "off" => Ok(GeometricInvariance::Off),
        "mirror-flip" => Ok(GeometricInvariance::MirrorFlip),
        "mirror-flip-rotate90" => Ok(GeometricInvariance::MirrorFlipRotate90),
        _ => Err(format!("unsupported geometricInvariance: {value}")),
    }
}

fn heic_decoder_name() -> &'static str {
    if cfg!(target_os = "macos") && Path::new("/usr/bin/sips").is_file() {
        "sips"
    } else {
        "none"
    }
}

fn is_heic(path: &Path) -> bool {
    matches!(extension(path).as_deref(), Some("heic" | "heif"))
}

fn extension(path: &Path) -> Option<String> {
    path.extension()
        .and_then(|value| value.to_str())
        .map(|value| value.to_ascii_lowercase())
}

fn collect_photos(
    request: &Request,
    extensions: &[String],
    stop: &AtomicBool,
    progress: &mut impl FnMut(serde_json::Value),
    warnings: &mut Vec<String>,
) -> Result<Vec<PathBuf>, String> {
    let mut photos = Vec::new();
    for directory in &request.directories {
        if stop.load(Ordering::Relaxed) {
            break;
        }
        if !directory.is_dir() {
            warnings.push(format!("SKIP_MISSING_DIR {}", directory.display()));
            continue;
        }
        walk_dir(directory, request.recursive, extensions, request.minimum_bytes, stop, &mut photos, warnings)?;
        progress(progress_event("collect", photos.len(), photos.len(), "正在收集照片"));
    }
    photos.sort();
    photos.dedup();
    Ok(photos)
}

fn walk_dir(
    directory: &Path,
    recursive: bool,
    extensions: &[String],
    minimum_bytes: u64,
    stop: &AtomicBool,
    photos: &mut Vec<PathBuf>,
    warnings: &mut Vec<String>,
) -> Result<(), String> {
    let entries = match fs::read_dir(directory) {
        Ok(entries) => entries,
        Err(error) => {
            warnings.push(format!("SKIP_UNREADABLE {} {error}", directory.display()));
            return Ok(());
        }
    };
    for entry in entries {
        if stop.load(Ordering::Relaxed) {
            return Ok(());
        }
        let entry = match entry {
            Ok(entry) => entry,
            Err(error) => {
                warnings.push(format!("SKIP_ENTRY {} {error}", directory.display()));
                continue;
            }
        };
        let path = entry.path();
        let metadata = match fs::symlink_metadata(&path) {
            Ok(metadata) => metadata,
            Err(error) => {
                warnings.push(format!("SKIP_STAT {} {error}", path.display()));
                continue;
            }
        };
        if metadata.file_type().is_symlink() {
            continue;
        }
        if metadata.is_dir() {
            if recursive {
                walk_dir(&path, true, extensions, minimum_bytes, stop, photos, warnings)?;
            }
            continue;
        }
        if !metadata.is_file() {
            continue;
        }
        let Some(ext) = extension(&path) else { continue };
        if !extensions.iter().any(|allowed| allowed == &ext) {
            continue;
        }
        if minimum_bytes > 0 && metadata.len() < minimum_bytes {
            continue;
        }
        photos.push(path);
    }
    Ok(())
}

fn stage_previews(
    photos: &[PathBuf],
    preview_dir: &Path,
    stop: &AtomicBool,
    progress: &mut impl FnMut(serde_json::Value),
    warnings: &mut Vec<String>,
) -> Result<(HashMap<String, PathBuf>, HashMap<PathBuf, Preview>), String> {
    let mut staged_names = HashMap::new();
    let mut previews = HashMap::new();
    let mut index = 0_u32;
    for path in photos {
        if stop.load(Ordering::Relaxed) {
            break;
        }
        let ext = extension(path).unwrap_or_default();
        let staged = if ext == "gif" {
            index += 1;
            let dest = preview_dir.join(format!("preview-{index}.png"));
            match convert_gif(path, &dest) {
                Ok(()) => Some(dest),
                Err(error) => {
                    warnings.push(format!("GIF_DECODE_FAILED {} {error}", path.display()));
                    None
                }
            }
        } else if ext == "heic" || ext == "heif" {
            index += 1;
            let dest = preview_dir.join(format!("preview-{index}.jpg"));
            match convert_heic(path, &dest) {
                Ok(()) => Some(dest),
                Err(error) => {
                    warnings.push(format!("HEIC_DECODE_FAILED {} {error}", path.display()));
                    None
                }
            }
        } else {
            None
        };
        if let Some(dest) = staged {
            let (width, height) = image_size(&dest);
            staged_names.insert(dest.file_name().unwrap_or_default().to_string_lossy().into_owned(), path.clone());
            previews.insert(path.clone(), Preview { preview_path: dest, width, height });
        }
        progress(progress_event("prepare", index as usize, photos.len(), "正在准备预览"));
    }
    Ok((staged_names, previews))
}

fn convert_gif(src: &Path, dest: &Path) -> Result<(), String> {
    let image = image::open(src).map_err(|error| error.to_string())?;
    image.save(dest).map_err(|error| error.to_string())
}

fn convert_heic(src: &Path, dest: &Path) -> Result<(), String> {
    if heic_decoder_name() != "sips" {
        return Err("macOS sips is not available".into());
    }
    let status = Command::new("/usr/bin/sips")
        .args(["-s", "format", "jpeg", "-s", "formatOptions", "90", "--out"])
        .arg(dest)
        .arg(src)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map_err(|error| error.to_string())?;
    if !status.success() || !dest.is_file() {
        let _ = fs::remove_file(dest);
        return Err(format!("sips exited {status}"));
    }
    Ok(())
}

fn image_size(path: &Path) -> (u32, u32) {
    image::image_dimensions(path).unwrap_or((0, 0))
}

fn file_facts(path: &Path, preview: Option<&Preview>, difference: u32) -> PhotoFile {
    let metadata = fs::metadata(path).ok();
    let size = metadata.as_ref().map(|meta| meta.len()).unwrap_or(0);
    let modified = metadata
        .and_then(|meta| meta.modified().ok())
        .and_then(|time| time.duration_since(UNIX_EPOCH).ok())
        .map(|duration| duration.as_secs())
        .unwrap_or(0);
    let (width, height, preview_path) = if let Some(preview) = preview {
        (preview.width, preview.height, preview.preview_path.clone())
    } else {
        let (width, height) = image_size(path);
        (width, height, path.to_path_buf())
    };
    PhotoFile {
        path: path.display().to_string(),
        size,
        width,
        height,
        modified,
        difference,
        preview_path: preview_path.display().to_string(),
    }
}

fn configure_common(tool: &mut impl CommonData, request: &Request, extensions: Option<&[String]>) {
    tool.set_delete_method(DeleteMethod::None);
    tool.set_use_cache(false);
    tool.set_delete_outdated_cache(false);
    tool.set_recursive_search(request.recursive);
    tool.set_dry_run(true);
    if request.minimum_bytes > 0 {
        tool.set_minimal_file_size(request.minimum_bytes);
    }
    if let Some(extensions) = extensions {
        tool.set_allowed_extensions(extensions.to_vec());
    }
}

fn find_exact(
    request: &Request,
    extensions: &[String],
    stop: &Arc<AtomicBool>,
    previews: &HashMap<PathBuf, Preview>,
) -> Result<Vec<PhotoGroup>, String> {
    let params = DuplicateFinderParameters::new(CheckingMethod::Hash, HashType::Blake3, false, 0, 0, true);
    let mut finder = DuplicateFinder::new(params);
    configure_common(&mut finder, request, Some(extensions));
    finder.set_included_paths(request.directories.clone());
    finder.set_excluded_paths(vec![request.preview_dir.clone()]);
    debug_assert_eq!(finder.get_delete_method(), DeleteMethod::None);

    let (sender, receiver) = crossbeam_channel::unbounded();
    let printer = spawn_progress(receiver);
    finder.search(stop, Some(&sender));
    drop(sender);
    printer.join().ok();
    if let Some(critical) = finder.get_text_messages().critical.clone() {
        return Err(critical);
    }
    let mut groups = Vec::new();
    for vectors in finder.get_files_sorted_by_hash().values() {
        for vector in vectors {
            if vector.len() < 2 {
                continue;
            }
            let files = vector
                .iter()
                .map(|entry| file_facts(&entry.path, previews.get(&entry.path), 0))
                .collect();
            groups.push(PhotoGroup { files });
        }
    }
    Ok(groups)
}

fn find_similar(
    request: &Request,
    hash_alg: HashAlg,
    invariance: GeometricInvariance,
    staged_names: &HashMap<String, PathBuf>,
    previews: &HashMap<PathBuf, Preview>,
    stop: &Arc<AtomicBool>,
) -> Result<Vec<PhotoGroup>, String> {
    let params = SimilarImagesParameters::new(
        request.max_difference.min(40),
        request.hash_size,
        hash_alg,
        FilterType::Lanczos3,
        false,
        false,
        invariance,
    );
    let mut finder = SimilarImages::new(params);
    configure_common(&mut finder, request, None);
    let mut directories = request.directories.clone();
    if !staged_names.is_empty() {
        directories.push(request.preview_dir.clone());
    }
    finder.set_included_paths(directories);
    debug_assert_eq!(finder.get_delete_method(), DeleteMethod::None);

    let (sender, receiver) = crossbeam_channel::unbounded();
    let printer = spawn_progress(receiver);
    finder.search(stop, Some(&sender));
    drop(sender);
    printer.join().ok();
    if let Some(critical) = finder.get_text_messages().critical.clone() {
        return Err(critical);
    }

    let mut groups = Vec::new();
    for vector in finder.get_similar_images() {
        if vector.len() < 2 {
            continue;
        }
        let files = vector
            .iter()
            .map(|entry| {
                let original = remap_staged(&entry.path, &request.preview_dir, staged_names);
                let preview = previews.get(&original);
                let mut file = file_facts(&original, preview, entry.difference);
                if preview.is_none() && (file.width == 0 || file.height == 0) {
                    file.width = entry.width;
                    file.height = entry.height;
                }
                file
            })
            .collect();
        groups.push(PhotoGroup { files });
    }
    Ok(groups)
}

fn remap_staged(path: &Path, preview_dir: &Path, staged_names: &HashMap<String, PathBuf>) -> PathBuf {
    if !path.starts_with(preview_dir) {
        return path.to_path_buf();
    }
    path.file_name()
        .and_then(|name| staged_names.get(&name.to_string_lossy().into_owned()))
        .cloned()
        .unwrap_or_else(|| path.to_path_buf())
}

fn spawn_progress(receiver: crossbeam_channel::Receiver<ProgressData>) -> thread::JoinHandle<()> {
    thread::spawn(move || {
        while let Ok(update) = receiver.recv() {
            let stage = match update.stage {
                czkawka_core::common::progress_data::ToolStage::SimilarImages(_) => "similar",
                czkawka_core::common::progress_data::ToolStage::Duplicate(_) => "exact",
                _ => "scan",
            };
            emit(&serde_json::json!({
                "type": "progress",
                "stage": stage,
                "checked": update.entries_checked,
                "total": update.entries_to_check,
                "label": format!("{stage} {}/{}", update.entries_checked, update.entries_to_check),
            }));
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use image::{Rgb, RgbImage};
    use image::imageops;

    fn pattern() -> RgbImage {
        let mut image = RgbImage::new(48, 48);
        for (x, y, pixel) in image.enumerate_pixels_mut() {
            *pixel = if x < 14 && y < 10 {
                Rgb([240, 16, 16])
            } else {
                Rgb([16, (20 + x).min(255) as u8, (30 + y).min(255) as u8])
            };
        }
        image
    }

    #[test]
    fn delete_method_stays_off_and_rotation_is_grouped() {
        let root = tempfile::tempdir().unwrap();
        let photos = root.path().join("photos");
        let preview = root.path().join("preview");
        fs::create_dir_all(&photos).unwrap();
        let image = pattern();
        image.save(photos.join("original.png")).unwrap();
        image.save(photos.join("copy.png")).unwrap();
        imageops::rotate90(&image).save(photos.join("rotated.png")).unwrap();
        imageops::flip_horizontal(&image).save(photos.join("flipped.png")).unwrap();
        let mut other = RgbImage::new(48, 48);
        for (x, y, pixel) in other.enumerate_pixels_mut() {
            *pixel = if (x + y) % 6 < 3 { Rgb([0, 220, 40]) } else { Rgb([0, 0, 90]) };
        }
        other.save(photos.join("other.png")).unwrap();

        let request = Request {
            directories: vec![photos],
            recursive: true,
            exact: true,
            similar: true,
            minimum_bytes: 0,
            max_difference: 5,
            hash_size: 16,
            hash_alg: "Gradient".into(),
            geometric_invariance: "mirror-flip-rotate90".into(),
            preview_dir: preview,
            extensions: vec![],
            stop_file: None,
        };
        let output = scan(&request, |_| {}).unwrap();
        assert_eq!(output.heic_decoder, "none");
        let exact_names = names_in(&output.exact);
        assert!(exact_names.iter().any(|group| group.contains(&"original.png".to_string()) && group.contains(&"copy.png".to_string())), "{exact_names:?}");
        let similar_names = names_in(&output.similar);
        let grouped = similar_names.iter().any(|group| {
            group.contains(&"original.png".into())
                && group.contains(&"rotated.png".into())
                && group.contains(&"flipped.png".into())
                && !group.contains(&"other.png".into())
        });
        assert!(grouped, "similar groups: {similar_names:?}");
    }

    fn names_in(groups: &[PhotoGroup]) -> Vec<Vec<String>> {
        groups
            .iter()
            .map(|group| {
                group
                    .files
                    .iter()
                    .map(|file| Path::new(&file.path).file_name().unwrap().to_string_lossy().into_owned())
                    .collect()
            })
            .collect()
    }

    #[test]
    fn rejects_unknown_invariance() {
        assert!(parse_invariance("rotate-free").is_err());
        assert_eq!(parse_invariance("mirror-flip-rotate90").unwrap(), GeometricInvariance::MirrorFlipRotate90);
    }
}
