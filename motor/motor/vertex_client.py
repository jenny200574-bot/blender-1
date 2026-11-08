"""Configured Vertex client; no secret values in reports, no model fallback."""
import json
from pathlib import Path

def _cliente():
 from google import genai
 from google.genai import types
 from google.oauth2 import service_account
 cfg=json.loads((Path(__file__).resolve().parents[1]/'config/argon_transporte.json').read_text())
 cred=service_account.Credentials.from_service_account_file(cfg['existing_file'],scopes=['https://www.googleapis.com/auth/cloud-platform'])
 return genai.Client(vertexai=True,project=cfg['project'],location=cfg['location'],credentials=cred,http_options=types.HttpOptions(api_version='v1',base_url='https://aiplatform.googleapis.com',timeout=cfg['timeout_s']*1000,retry_options=types.HttpRetryOptions(attempts=1)))
