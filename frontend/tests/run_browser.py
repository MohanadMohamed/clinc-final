"""Disposable HTTPS browser integration. No persistent DB or fixed credentials."""
import getpass
import os
import secrets
import signal
import subprocess
import tempfile
import time
import sys
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[2]
PG=Path('/usr/lib/postgresql/18/bin')
tls_only = sys.argv[1:] == ['--tls-only']
http_dev_only = sys.argv[1:] == ['--http-dev-only']
render_demo_only = sys.argv[1:] == ['--render-demo-only']
static_only = tls_only or render_demo_only or sys.argv[1:] == ['--static-only']
if static_only and not (ROOT/'frontend/dist/index.html').is_file():
    raise RuntimeError('Run cd frontend && npm run build before --static-only')
with tempfile.TemporaryDirectory(prefix='clinic-browser-') as tmp:
    root=Path(tmp)
    cert,key=root/'cert.pem',root/'key.pem'
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run([str(PG/'initdb'),'-D',str(root/'db'),'-A','trust','--no-locale','-E','UTF8'],check=True,stdout=subprocess.DEVNULL)
    ctl=[str(PG/'pg_ctl'),'-D',str(root/'db')]
    subprocess.run(ctl+['-l',str(root/'pg.log'),'-o',f"-h '' -k {tmp} -p 55442",'-w','start'],check=True,stdout=subprocess.DEVNULL)
    url=f'postgresql+psycopg://{getpass.getuser()}@/postgres?host={tmp}&port=55442'
    origin = 'http://127.0.0.1:5173' if http_dev_only else 'https://localhost:8443' if static_only else 'https://localhost:5173'
    env={**os.environ,'CLINIC_DATABASE_URL':url,'CLINIC_MIGRATION_DATABASE_URL':url,'CLINIC_PUBLIC_ORIGIN':origin,'CLINIC_ENV':'development' if http_dev_only else 'production'}
    if render_demo_only:
        env.update({'RENDER':'true','CLINIC_DEPLOYMENT':'render_demo','CLINIC_DEMO_PUBLIC_ENABLED':'true'})
        env.pop('RENDER_EXTERNAL_HOSTNAME',None)
    else:
        env.pop('RENDER',None)
        env.pop('CLINIC_DEPLOYMENT',None)
        env.pop('CLINIC_DEMO_PUBLIC_ENABLED',None)
    if http_dev_only:
        env.pop('CLINIC_TEST_CERT',None)
        env.pop('CLINIC_TEST_KEY',None)
    else:
        env.update({'CLINIC_TEST_CERT':str(cert),'CLINIC_TEST_KEY':str(key)})
    password=secrets.token_urlsafe(24)
    servers=[]
    try:
        subprocess.run([str(ROOT/'backend/.venv/bin/alembic'),'upgrade','head'],cwd=ROOT/'backend',env=env,check=True,stdout=subprocess.DEVNULL)
        code='from app.core.db import build_engine,build_session_factory; from app.bootstrap import bootstrap; from app.models.auth import User; from app.services.auth import HASHER; import os; e=build_engine(os.environ["CLINIC_DATABASE_URL"]); s=build_session_factory(e); db=s(); bootstrap(db,"synthetic.doctor",os.environ["TEST_PASSWORD"]); db.add(User(username="synthetic.reception",password_hash=HASHER.hash(os.environ["TEST_PASSWORD"]),role="receptionist")); db.commit(); db.close(); e.dispose()'
        subprocess.run([str(ROOT/'backend/.venv/bin/python'),'-c',code],cwd=ROOT/'backend',env={**env,'TEST_PASSWORD':password},check=True)
        api_args=[str(ROOT/'backend/.venv/bin/uvicorn'),'app.main:app','--host','127.0.0.1','--port','8000' if http_dev_only else '8443']
        if not http_dev_only: api_args+=['--ssl-certfile',str(cert),'--ssl-keyfile',str(key)]
        api_args+=['--no-access-log','--no-proxy-headers']
        if http_dev_only:
            # Exercise the documented launcher from outside the repository.
            # A separate process group also contains uvicorn's reload child.
            servers.append(subprocess.Popen([str(ROOT/'scripts/dev_local.sh')],cwd=root,env=env,start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        else:
            servers.append(subprocess.Popen(api_args,cwd=ROOT/'backend',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        if not static_only and not http_dev_only:
            servers.append(subprocess.Popen(['npm','run','dev','--','--host','127.0.0.1'],cwd=ROOT/'frontend',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        for _ in range(80):
            try:
                import ssl
                urlopen(origin + ('/app/' if static_only else '/'),context=None if http_dev_only else ssl.create_default_context(cafile=str(cert)),timeout=1).close()
                urlopen(origin + '/api/health/ready',context=None if http_dev_only else ssl.create_default_context(cafile=str(cert)),timeout=1).close()
                break
            except Exception: time.sleep(.25)
        else: raise RuntimeError('Test servers failed to start')
        # The full flow reaches the per-account login throttle; isolated QA uses
        # its own disposable cluster rather than weakening production limits.
        scripts = ['render_demo.mjs'] if render_demo_only else ['http_dev.mjs'] if http_dev_only else ['tls_probe.py'] if tls_only else ['static.mjs'] if static_only else ['qa.mjs'] if sys.argv[1:] == ['--qa-only'] else ['billing.mjs'] if sys.argv[1:] == ['--billing-only'] else ['browser.mjs', 'appointments.mjs', 'visits.mjs', 'billing.mjs']
        for script in scripts:
            runner = str(ROOT/'backend/.venv/bin/python') if script.endswith('.py') else 'node'
            subprocess.run([runner,f'tests/{script}'],cwd=ROOT/'frontend',env={**env,'TEST_PASSWORD':password},check=True)
        if len(scripts) > 1:
            servers[0].terminate()
            servers[0].wait(timeout=5)
            servers[0]=subprocess.Popen([str(ROOT/'backend/.venv/bin/uvicorn'),'app.main:app','--host','127.0.0.1','--port','8443','--ssl-certfile',str(cert),'--ssl-keyfile',str(key),'--no-access-log','--no-proxy-headers'],cwd=ROOT/'backend',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            time.sleep(1)
            subprocess.run(['node','tests/after_restart.mjs'],cwd=ROOT/'frontend',env={**env,'TEST_PASSWORD':password},check=True)
    finally:
        for server in reversed(servers):
            if http_dev_only:
                try: os.killpg(server.pid,signal.SIGTERM)
                except ProcessLookupError: pass
            else: server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if http_dev_only: os.killpg(server.pid,signal.SIGKILL)
                else: server.kill()
                server.wait(timeout=5)
        subprocess.run(ctl+['-m','fast','-w','stop'],check=True,stdout=subprocess.DEVNULL)
