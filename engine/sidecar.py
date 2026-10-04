"""Executable entry point for the bundled desktop engine."""

from organize_gui.rpc_server import RpcServer


if __name__ == "__main__":
    RpcServer().run()
