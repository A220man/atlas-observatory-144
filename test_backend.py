import asyncio
import httpx
import subprocess
import time
import sys

async def test_backend():
    # Start the backend server
    proc = subprocess.Popen([
        sys.executable, '-m', 'uvicorn', 'backend.main:app', 
        '--host', '0.0.0.0', '--port', '8000'
    ], cwd='/var/lib/alan-portfolio/workspaces/ryan/atlas-observatory-144')
    
    try:
        # Wait for server to start
        time.sleep(3)
        
        async with httpx.AsyncClient(base_url='http://localhost:8000') as client:
            # Test health
            resp = await client.get('/health')
            assert resp.status_code == 200
            assert resp.json()['status'] == 'ok'
            print('✓ Health check passed')
            
            # Create project
            resp = await client.post('/projects', json={'name': 'Test Project', 'path': '/tmp/test'})
            assert resp.status_code == 200
            project = resp.json()
            project_id = project['id']
            print(f'✓ Created project: {project_id}')
            
            # Create session
            resp = await client.post('/sessions', json={'project_id': project_id, 'title': 'Test Session'})
            assert resp.status_code == 200
            session = resp.json()
            session_id = session['id']
            print(f'✓ Created session: {session_id}')
            
            # Add observation
            resp = await client.post('/observations', json={
                'session_id': session_id,
                'type': 'bugfix',
                'title': 'Fix login bug',
                'narrative': 'Fixed the login authentication issue',
                'metadata': {'severity': 'high'}
            })
            assert resp.status_code == 200
            print('✓ Created observation')
            
            # Query context
            resp = await client.post('/context', json={
                'project_id': project_id,
                'query': 'login',
                'limit': 10
            })
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert 'login' in data[0]['title'].lower() or 'login' in data[0]['narrative'].lower()
            print('✓ Context search passed')
            
            print('\n✓ All tests passed!')
    finally:
        proc.terminate()
        proc.wait()

if __name__ == '__main__':
    asyncio.run(test_backend())
