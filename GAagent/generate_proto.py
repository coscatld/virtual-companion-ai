"""Regenerate Python bindings from the shared Java/Python API contract."""

from pathlib import Path

from grpc_tools import protoc


root = Path(__file__).resolve().parent
source = root.parent / "VR_Gfriend" / "src" / "main" / "proto"
output = root / "virtual_lover_agent" / "protos"

status = protoc.main([
    "grpc_tools.protoc",
    f"-I{source}",
    f"--python_out={output}",
    f"--pyi_out={output}",
    f"--grpc_python_out={output}",
    str(source / "agent_proto.proto"),
])
if status != 0:
    raise SystemExit(status)

grpc_output = output / "agent_proto_pb2_grpc.py"
generated = grpc_output.read_text(encoding="utf-8")
grpc_output.write_text(
    generated.replace("import agent_proto_pb2 as", "from . import agent_proto_pb2 as"),
    encoding="utf-8",
    newline="\n",
)
