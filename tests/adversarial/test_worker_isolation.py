import json
import subprocess

from autodiscover.experiments.runner import sandbox_command


def test_native_worker_profile_blocks_host_read_write_and_network(tmp_path, monkeypatch):
    secret = tmp_path / "host-private-file"
    secret.write_text("host-secret-sentinel")
    script = tmp_path / "trusted_security_probe.py"
    script.write_text("""import json,socket,sys,os
checks={}
for name,path,mode in [('read',sys.argv[1],'r'),('write',sys.argv[2],'w')]:
 try:
  with open(path,mode) as f:
   if mode=='r': f.read()
   else: f.write('unauthorized')
  checks[name]=False
 except PermissionError: checks[name]=True
try:
 s=socket.socket(); s.connect(('127.0.0.1',9)); checks['network']=False
except PermissionError: checks['network']=True
checks['secret_env_absent']='SENTINEL_API_KEY' not in os.environ
print(json.dumps(checks))
""")
    monkeypatch.setenv("SENTINEL_API_KEY", "never-inherit-this")
    command = sandbox_command(script) + [str(secret), str(tmp_path / "forbidden-write")]
    result = subprocess.run(  # noqa: S603 - fixed trusted test commands, no shell
        command,
        capture_output=True,
        text=True,
        check=True,
        env={"PATH": "", "PYTHONHASHSEED": "0"},
        cwd="/",
    )  # noqa: S603
    assert json.loads(result.stdout) == {
        "read": True,
        "write": True,
        "network": True,
        "secret_env_absent": True,
    }
    assert "host-secret-sentinel" not in result.stdout
    assert not (tmp_path / "forbidden-write").exists()
