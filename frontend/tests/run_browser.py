"""Disposable HTTPS browser integration. No persistent DB or fixed credentials."""
import getpass
import os
import secrets
import subprocess
import tempfile
import time
import sys
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[2]
PG=Path('/usr/lib/postgresql/18/bin')
with tempfile.TemporaryDirectory(prefix='clinic-browser-') as tmp:
    root=Path(tmp)
    cert,key=root/'cert.pem',root/'key.pem'
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run([str(PG/'initdb'),'-D',str(root/'db'),'-A','trust','--no-locale','-E','UTF8'],check=True,stdout=subprocess.DEVNULL)
    ctl=[str(PG/'pg_ctl'),'-D',str(root/'db')]
    subprocess.run(ctl+['-l',str(root/'pg.log'),'-o',f"-h '' -k {tmp} -p 55442",'-w','start'],check=True,stdout=subprocess.DEVNULL)
    url=f'postgresql+psycopg://{getpass.getuser()}@/postgres?host={tmp}&port=55442'
    env={**os.environ,'CLINIC_DATABASE_URL':url,'CLINIC_MIGRATION_DATABASE_URL':url,'CLINIC_PUBLIC_ORIGIN':'https://localhost:5173','CLINIC_TEST_CERT':str(cert),'CLINIC_TEST_KEY':str(key)}
    password=secrets.token_urlsafe(24)
    servers=[]
    try:
        subprocess.run([str(ROOT/'backend/.venv/bin/alembic'),'upgrade','head'],cwd=ROOT/'backend',env=env,check=True,stdout=subprocess.DEVNULL)
        code='from app.core.db import build_engine,build_session_factory; from app.bootstrap import bootstrap; from app.models.auth import User; from app.services.auth import HASHER; import os; e=build_engine(os.environ["CLINIC_DATABASE_URL"]); s=build_session_factory(e); db=s(); bootstrap(db,"synthetic.doctor",os.environ["TEST_PASSWORD"]); db.add(User(username="synthetic.reception",password_hash=HASHER.hash(os.environ["TEST_PASSWORD"]),role="receptionist")); db.commit(); db.close(); e.dispose()'
        subprocess.run([str(ROOT/'backend/.venv/bin/python'),'-c',code],cwd=ROOT/'backend',env={**env,'TEST_PASSWORD':password},check=True)
        servers.append(subprocess.Popen([str(ROOT/'backend/.venv/bin/uvicorn'),'app.main:app','--host','127.0.0.1','--port','8443','--ssl-certfile',str(cert),'--ssl-keyfile',str(key),'--no-access-log','--no-proxy-headers'],cwd=ROOT/'backend',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        servers.append(subprocess.Popen(['npm','run','dev','--','--host','127.0.0.1'],cwd=ROOT/'frontend',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        for _ in range(80):
            try:
                import ssl
                urlopen('https://localhost:5173',context=ssl._create_unverified_context(),timeout=1).close()
                break
            except Exception: time.sleep(.25)
        else: raise RuntimeError('HTTPS test servers failed to start')
        # The full flow reaches the per-account login throttle; isolated QA uses
        # its own disposable cluster rather than weakening production limits.
        scripts = ['qa.mjs'] if sys.argv[1:] == ['--qa-only'] else ['billing.mjs'] if sys.argv[1:] == ['--billing-only'] else ['browser.mjs', 'appointments.mjs', 'visits.mjs', 'billing.mjs']
        for script in scripts:
            subprocess.run(['node',f'tests/{script}'],cwd=ROOT/'frontend',env={**env,'TEST_PASSWORD':password},check=True)
        servers[0].terminate()
        servers[0].wait(timeout=5)
        servers[0]=subprocess.Popen([str(ROOT/'backend/.venv/bin/uvicorn'),'app.main:app','--host','127.0.0.1','--port','8443','--ssl-certfile',str(cert),'--ssl-keyfile',str(key),'--no-access-log','--no-proxy-headers'],cwd=ROOT/'backend',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        time.sleep(1)
        if len(scripts) > 1:
            subprocess.run(['node','tests/after_restart.mjs'],cwd=ROOT/'frontend',env={**env,'TEST_PASSWORD':password},check=True)
    finally:
        for server in reversed(servers):
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill()
        subprocess.run(ctl+['-m','fast','-w','stop'],check=True,stdout=subprocess.DEVNULL)
