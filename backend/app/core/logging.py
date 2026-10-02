import json
import logging
from datetime import datetime, timezone

class JsonFormatter(logging.Formatter):
    def format(self, record):
        data={"timestamp":datetime.now(timezone.utc).isoformat(),"level":record.levelname,"logger":record.name,"message":record.getMessage()}
        for key in ("incident_id","event","details","error_type"):
            if hasattr(record,key): data[key]=getattr(record,key)
        return json.dumps(data,default=str)

def configure_logging():
    handler=logging.StreamHandler();handler.setFormatter(JsonFormatter())
    root=logging.getLogger();root.handlers.clear();root.addHandler(handler);root.setLevel(logging.INFO)
