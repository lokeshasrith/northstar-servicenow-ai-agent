from abc import ABC, abstractmethod
import os
import uuid
import httpx

class ServiceNowAdapter(ABC):
    @abstractmethod
    def list_incidents(self): ...
    @abstractmethod
    def update_incident(self, sys_id: str, fields: dict): ...

class MockServiceNowAdapter(ServiceNowAdapter):
    records: dict[str,dict] = {}
    counter = 10000
    def list_incidents(self): return list(self.records.values())
    def get_incident(self,sys_id): return self.records.get(sys_id)
    def update_incident(self, sys_id: str, fields: dict):
        if sys_id not in self.records: raise KeyError("Mock ServiceNow incident not found")
        self.records[sys_id].update(fields);return self.records[sys_id]
    def create_incident(self, fields: dict):
        type(self).counter+=1;sys_id="mock-"+uuid.uuid4().hex[:12]
        row={"sys_id":sys_id,"number":f"INC{type(self).counter}","state":"1","priority":"4",**fields}
        self.records[sys_id]=row;return row
    def assign_incident(self,sys_id,group=None,assignee=None):
        fields={}
        if group: fields["assignment_group"]=group
        if assignee: fields["assigned_to"]=assignee
        return self.update_incident(sys_id,fields)
    def add_work_notes(self,sys_id,notes):
        row=self.records[sys_id];row["work_notes"]=(row.get("work_notes","")+"\n"+notes).strip();return row
    def add_comment(self,sys_id,comment):
        row=self.records[sys_id];row["comments"]=(row.get("comments","")+"\n"+comment).strip();return row
    def get_knowledge(self,query):
        from app.knowledge.service import kb
        return [{"number":item["id"],"short_description":item["title"],"text":item["snippet"],"source":item["source"]} for item in kb.search(query,5)]

class RealServiceNowAdapter(ServiceNowAdapter):
    """Table API client. Credentials are read only from environment settings."""
    def __init__(self, instance_url: str | None = None, username: str | None = None, password: str | None = None):
        self.base = (instance_url or os.getenv("SERVICENOW_INSTANCE_URL", "")).rstrip("/")
        self.auth = (username or os.getenv("SERVICENOW_USERNAME", ""), password or os.getenv("SERVICENOW_PASSWORD", ""))
        if not self.base or not all(self.auth): raise ValueError("ServiceNow instance URL and credentials must be configured")
    def _request(self, method, table, sys_id=None, **kwargs):
        url=f"{self.base}/api/now/table/{table}" + (f"/{sys_id}" if sys_id else "")
        if method in {"POST","PATCH","PUT"}:
            params=kwargs.pop("params",{})
            params={**params,"sysparm_input_display_value":"true"}
            kwargs["params"]=params
        response=httpx.request(method,url,auth=self.auth,headers={"Accept":"application/json","Content-Type":"application/json"},timeout=20,**kwargs)
        response.raise_for_status(); return response.json().get("result")
    def list_incidents(self): return self._request("GET","incident",params={"sysparm_limit":100})
    def get_incident(self, sys_id): return self._request("GET","incident",sys_id)
    def create_incident(self, fields): return self._request("POST","incident",json=fields)
    def find_by_correlation_id(self, correlation_id):
        result=self._request("GET","incident",params={"sysparm_query":f"correlation_id={correlation_id}","sysparm_limit":1})
        return result[0] if result else None
    def update_incident(self, sys_id, fields): return self._request("PATCH","incident",sys_id,json=fields)
    def assign_incident(self, sys_id, group=None, assignee=None):
        fields={}
        if group: fields["assignment_group"]=group
        if assignee: fields["assigned_to"]=assignee
        return self.update_incident(sys_id,fields)
    def add_work_notes(self, sys_id, notes): return self.update_incident(sys_id,{"work_notes":notes})
    def add_comment(self, sys_id, comment): return self.update_incident(sys_id,{"comments":comment})
    def get_knowledge(self, query): return self._request("GET","kb_knowledge",params={"sysparm_query":f"short_descriptionLIKE{query}","sysparm_limit":10})
