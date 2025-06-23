from datetime import datetime
from email.policy import default
import logging
from mongoengine import (
    Document,
    EmbeddedDocument,
    EmbeddedDocumentField,
    EmbeddedDocumentListField,
    StringField,
    IntField,
    ListField,
    EmailField,
    DateTimeField,
)

# --- Reusable Merge Logic ---
def merge_documents(instance, updates: dict):
    if not instance:
        raise ValueError("Instance must not be None")

    for key, value in updates.items():
        field = instance._fields.get(key)
        if not field:
            continue

        current_value = getattr(instance, key, None)

        if isinstance(field, EmbeddedDocumentField):
            if current_value:
                merged = merge_documents(current_value, value)
                setattr(instance, key, merged)
            else:
                setattr(instance, key, field.document_type(**value))

        elif isinstance(field, EmbeddedDocumentListField):
            existing = current_value or []
            existing_dicts = [e.to_mongo().to_dict() for e in existing]
            new_dicts = [v.to_mongo().to_dict() if hasattr(v, 'to_mongo') else v for v in value]
            combined = existing_dicts + [v for v in new_dicts if v not in existing_dicts]
            result_objs = [field.field.document_type(**d) for d in combined]
            setattr(instance, key, result_objs)

        elif isinstance(value, list):
            merged_list = list(set((current_value or []) + value))
            setattr(instance, key, merged_list)

        else:
            setattr(instance, key, value)

    return instance

# --- Link Metadata ---
class PathEntry(EmbeddedDocument):
    path = StringField(required=True)
    status = IntField()
    size = IntField()
    words = IntField()
    line = IntField()

class RobotsTxtEntry(EmbeddedDocument):
    path = StringField(required=True)
    type = StringField(choices=["allowed", "disallowed", "sitemap"], required=True)

class FormFieldEntry(EmbeddedDocument):
    action = StringField(required=True)
    method = StringField(required=True)
    fields = ListField(StringField())
    can_found_at = ListField(StringField())

class TechnologyEntry(EmbeddedDocument):
    name = StringField(required=True)
    version = StringField(default="")
    categories = ListField(StringField())
    confidence = StringField()
    group = StringField()
    detected_by = StringField()

    def to_dict(self):
        return {
            'name': self.name,
            'version': self.version,
            'category': self.categories,
            'confidence': self.confidence,
            'group': self.group,
            'detected_by': self.detected_by
        }

class ServiceLinks(EmbeddedDocument):
    urls = ListField(StringField())
    emails = ListField(EmailField())
    images = ListField(StringField())
    videos = ListField(StringField())
    audio = ListField(StringField())
    comments = ListField(StringField())
    pages = ListField(StringField())
    parameters = ListField(StringField())
    subdomain_links = ListField(StringField())
    static_files = ListField(StringField())
    javascript_files = ListField(StringField())
    external_files = ListField(StringField())
    other_links = ListField(StringField())
    form_fields = EmbeddedDocumentListField(FormFieldEntry)
    robots_txt = EmbeddedDocumentListField(RobotsTxtEntry)
    directories = EmbeddedDocumentListField(PathEntry)

    def update(self, updates: dict):
        if isinstance(updates, ServiceLinks):
            updates = updates.to_mongo().to_dict()
        return merge_documents(self, updates)

class ServiceInfo(EmbeddedDocument):
    protocol = StringField(required=True, default="tcp")
    port = IntField(required=True)
    state = StringField(default="open")
    reason = StringField()
    name = StringField()
    product = StringField()
    version = StringField()
    extrainfo = StringField()
    conf = StringField()
    cpe = ListField(StringField())
    
    def to_dict(self):
        return {
            'protocol': self.protocol,
            'port': self.port,
            'state': self.state,
            'reason': self.reason,
            'name': self.name,
            'product': self.product,
            'version': self.version,
            'extrainfo': self.extrainfo,
            'conf': self.conf,
            'cpe': self.cpe,
        }

# --- VHost-Level Recon ---
class HostInfo(EmbeddedDocument):
    domain = StringField(required=True)
    port = IntField(default=80)
    technologies = EmbeddedDocumentListField(TechnologyEntry, default=[])
    links = EmbeddedDocumentField(ServiceLinks, default=lambda: ServiceLinks())
    
    def to_dict(self):
        return {
            'domain': self.domain,
            'port': self.port,
            'technologies': self.technologies,
            'links': self.links,
        }
    
# --- Primary Recon Target (by IP) ---
class TargetInfo(Document):
    hostname = StringField(required=False)
    ip_address = StringField(required=True)
    operating_system = StringField()
    virtual_hosts = EmbeddedDocumentListField(HostInfo, default=[])
    services = EmbeddedDocumentListField(ServiceInfo)

    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'targets',
        'indexes': [
            {'fields': ['hostname'], 'unique': True, 'sparse': True},
            {'fields': ['ip_address'], 'unique': True}
        ]
    }

    def commit(self):
        self.updated_at = datetime.utcnow()
        return self.save()

    def get_vhost(self, domain):
        return next((vh for vh in self.virtual_hosts if vh.domain == domain), None)
    
    def clean(self):
        """
        Custom validation to ensure no duplicate HostInfo entries based on 'domain'.
        This method is called automatically before save().
        """
        vhosts = set()
        
        for host in self.virtual_hosts:
            if host.domain in vhosts:
                logging.debug(f"Validation: Duplicate virtual host domain '{host.domain}' found. Removing it.")
                self.virtual_hosts.remove(host) # Remove the duplicate
            else:
                vhosts.add(host.domain)