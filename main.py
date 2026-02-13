from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import re

try:
    import paramiko
except Exception:
    paramiko = None

app = FastAPI()
templates = Jinja2Templates(directory="templates")

_IPV4_RE = re.compile(
    r"^(25[0-5]|2[0-4]\d|1?\d?\d)"
    r"(\.(25[0-5]|2[0-4]\d|1?\d?\d)){3}$"
)
_HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-\.]{0,253}[A-Za-z0-9]$")


def _is_ipv4(value: str) -> bool:
    return bool(_IPV4_RE.match(value.strip()))


def _is_host_or_ipv4(value: str) -> bool:
    value = value.strip()
    return bool(_IPV4_RE.match(value)) or bool(_HOST_RE.match(value))


def _run_remote_command(host: str, user: str, password: str, cmd: str) -> str:
    if paramiko is None:
        return "Error: paramiko is not installed. Install it with: pip install paramiko"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=host,
            username=user,
            password=password,
            timeout=5,
            auth_timeout=5,
            banner_timeout=5,
        )
        stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        rc = stdout.channel.recv_exit_status()
    except Exception as e:
        return f"Error: {e}"
    finally:
        try:
            client.close()
        except Exception:
            pass

    if err:
        return f"{out}\n{err}\n(exit {rc})".strip()
    return f"{out}\n(exit {rc})".strip()


@app.get("/", response_class=HTMLResponse)
def form(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": "",
            "ip": "",
            "username": "serwis3c",
            "password": "",
            "last_action": "",
            "ping_target": "",
            "route_get_target": "",
        }
    )

@app.post("/", response_class=HTMLResponse)
def run_command(
    request: Request,
    ip: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    action: str = Form(...),
    ping_target: str = Form(""),
    route_get_target: str = Form(""),
):
    ip = ip.strip()
    username = username.strip()
    ping_target = ping_target.strip()
    route_get_target = route_get_target.strip()

    if not _is_ipv4(ip):
        output = "Error: invalid IPv4 address."
    elif not username:
        output = "Error: username is required."
    else:
        if action == "ping":
            if not ping_target:
                output = "Error: ping target is required."
                cmd = ""
            elif not _is_host_or_ipv4(ping_target):
                output = "Error: invalid ping target."
                cmd = ""
            else:
                cmd = f"ping -c 4 {ping_target}"
        elif action == "ip_route":
            cmd = "ip route"
        elif action == "ip_route_get":
            if not route_get_target:
                output = "Error: route target is required."
                cmd = ""
            elif not _is_host_or_ipv4(route_get_target):
                output = "Error: invalid route target."
                cmd = ""
            else:
                cmd = f"ip route get {route_get_target}"
        elif action == "docker_ps":
            cmd = "docker ps"
        else:
            cmd = ""
            output = "Error: unknown action."

        if cmd:
            output = _run_remote_command(ip, username, password, cmd)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": output,
            "ip": ip,
            "username": username or "serwis3c",
            "password": password,
            "last_action": action,
            "ping_target": ping_target,
            "route_get_target": route_get_target,
        }
    )
