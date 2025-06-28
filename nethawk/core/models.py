from datetime import datetime
from mongoengine import *

# ----------------------------------
# Main Recon Target Model
# ----------------------------------

class TargetInfo(Document):
    hostname = StringField()
    ip_address = StringField(required=True, unique=True)
    operating_system = StringField()
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    virtual_hosts = ListField(ReferenceField('HostInfo'))
    services = ListField(ReferenceField('ServiceInfo'))

    meta = {
        'collection': 'target_info',
        'indexes': ['ip_address']
    }

    def to_dict(self):
        return {
            'id': str(self.id),
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'operating_system': self.operating_system,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'virtual_hosts': [vh.to_dict() for vh in HostInfo.objects(target=self)],
            'services': [s.to_dict() for s in ServiceInfo.objects(target=self)]
        }

    @classmethod
    def get_or_create(cls, ip_address, **kwargs):
        existing = cls.objects(ip_address=ip_address).first()
        if existing:
            return existing
        instance = cls(ip_address=ip_address, **kwargs)
        instance.save()
        return instance


# ----------------------------------
# Host / Virtual Host (Domain) Info
# ----------------------------------

class HostInfo(Document):
    domain = StringField(required=True)
    port = IntField(default=80)
    target = ReferenceField('TargetInfo', reverse_delete_rule=CASCADE)

    technologies = ListField(ReferenceField('TechnologyEntry'))
    links = ReferenceField('ServiceLinks')

    meta = {
        'collection': 'host_info',
        'indexes': [{'fields': ['domain', 'target'], 'unique': True}]
    }

    def to_dict(self):
        return {
            'id': str(self.id),
            'domain': self.domain,
            'port': self.port,
            'target_id': str(self.target.id) if self.target else None,
            'technologies': [t.to_dict() for t in TechnologyEntry.objects(host=self)],
            'links': [l.to_dict() for l in ServiceLinks.objects(host=self)],
        }
    
    @classmethod
    def get_or_create(cls, domain, target, port=80, **kwargs):
        existing = cls.objects(domain=domain, target=target).first()
        if existing:
            return existing
        instance = cls(domain=domain, target=target, port=port, **kwargs)
        instance.save()
        return instance


# ----------------------------------
# Network Service Info (Port Scan Results)
# ----------------------------------

class ServiceInfo(Document):
    target = ReferenceField('TargetInfo', reverse_delete_rule=CASCADE)

    protocol = StringField(default="tcp")
    port = IntField(required=True)
    state = StringField(default="open")
    reason = StringField()
    name = StringField()
    product = StringField()
    version = StringField()
    extrainfo = StringField()
    conf = StringField()
    cpe = ListField(StringField())

    meta = {
        'collection': 'service_info',
        'indexes': [
            {'fields': ['target', 'port'], 'unique': True}
        ]
    }

    def to_dict(self):
        return {
            'id': str(self.id),
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
            'target_id': str(self.target.id) if self.target else None
        }

    @classmethod
    def get_or_create(cls, port, target, **kwargs):
        existing = cls.objects(port=port, target=target).first()
        if existing:
            return existing
        instance = cls(port=port, target=target, **kwargs)
        instance.save()
        return instance


# ----------------------------------
# Service Links (Recon Data per Host)
# ----------------------------------

class ServiceLinks(Document):
    host = ReferenceField('HostInfo', reverse_delete_rule=CASCADE)

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

    form_fields = ListField(ReferenceField('FormFieldEntry'))
    robots_txt = ListField(ReferenceField('RobotsTxtEntry'))
    directories = ListField(ReferenceField('PathEntry'))

    meta = {
        'collection': 'service_links',
        'indexes': ['host']
    }

    def to_dict(self):
        return {
            'id': str(self.id),
            'host_id': str(self.host.id) if self.host else None,
            'urls': self.urls,
            'emails': self.emails,
            'images': self.images,
            'videos': self.videos,
            'audio': self.audio,
            'comments': self.comments,
            'pages': self.pages,
            'parameters': self.parameters,
            'subdomain_links': self.subdomain_links,
            'static_files': self.static_files,
            'javascript_files': self.javascript_files,
            'external_files': self.external_files,
            'other_links': self.other_links,
            'form_fields': [f.to_dict() for f in FormFieldEntry.objects(service_links=self)],
            'robots_txt': [r.to_dict() for r in RobotsTxtEntry.objects(service_links=self)],
            'directories': [d.to_dict() for d in PathEntry.objects(service_links=self)]
        }

    @classmethod
    def get_or_create(cls, host):
        existing = cls.objects(host=host).first()
        if existing:
            return existing
        instance = cls(host=host)
        instance.save()
        return instance


# ----------------------------------
# Technologies Detected on Host
# ----------------------------------

class TechnologyEntry(Document):
    name = StringField(required=True)
    version = StringField(default="")
    categories = ListField(StringField())
    confidence = StringField()
    group = StringField()
    detected_by = StringField()
    host = ReferenceField('HostInfo', reverse_delete_rule=CASCADE)

    meta = {
        'collection': 'technology_entry',
        'indexes': [{'fields': ['name', 'version', 'host'], 'unique': True}]
    }

    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'version': self.version,
            'categories': self.categories,
            'confidence': self.confidence,
            'group': self.group,
            'detected_by': self.detected_by,
            'host_id': str(self.host.id) if self.host else None
        }

    @classmethod
    def get_or_create(cls, name, version, host, **kwargs):
        existing = cls.objects(name=name, version=version, host=host).first()
        if existing:
            return existing
        instance = cls(name=name, version=version, host=host, **kwargs)
        instance.save()
        return instance


# ----------------------------------
# Form Fields (Web Forms)
# ----------------------------------

class FormFieldEntry(Document):
    service_links = ReferenceField('ServiceLinks', reverse_delete_rule=CASCADE)

    action = StringField(required=True)
    method = StringField(required=True)
    fields = ListField(StringField())
    can_found_at = ListField(StringField())

    meta = {
        'collection': 'form_field_entry',
        'indexes': [{'fields': ['action', 'service_links'], 'unique': True}]
    }

    def to_dict(self):
        return {
            'id': str(self.id),
            'action': self.action,
            'method': self.method,
            'fields': self.fields,
            'can_found_at': self.can_found_at,
            'service_links_id': str(self.service_links.id) if self.service_links else None
        }

    @classmethod
    def get_or_create(cls, action, service_links, method="GET", **kwargs):
        existing = cls.objects(action=action, service_links=service_links).first()
        if existing:
            return existing
        instance = cls(action=action, method=method, service_links=service_links, **kwargs)
        instance.save()
        return instance


# ----------------------------------
# Robots.txt Entry
# ----------------------------------

class RobotsTxtEntry(Document):
    service_links = ReferenceField('ServiceLinks', reverse_delete_rule=CASCADE)

    path = StringField(required=True)
    type = StringField(choices=["allowed", "disallowed", "sitemap"], required=True)
    status = StringField(null=True)

    meta = {
        'collection': 'robots_txt_entry',
        'indexes': [{'fields': ['path', 'service_links'], 'unique': True}]
    }

    def to_dict(self):
        return {
            'id': str(self.id),
            'path': self.path,
            'type': self.type,
            'service_links_id': str(self.service_links.id) if self.service_links else None
        }

    @classmethod
    def get_or_create(cls, path, type, status, service_links):
        existing = cls.objects(path=path, type=type, status=status, service_links=service_links).first()
        if existing:
            return existing
        instance = cls(path=path, type=type, status=status, service_links=service_links)
        instance.save()
        return instance


# ----------------------------------
# Directory / Path Entry (like Gobuster output)
# ----------------------------------

class PathEntry(Document):
    service_links = ReferenceField('ServiceLinks', reverse_delete_rule=CASCADE)

    path = StringField(required=True)
    status = IntField()
    size = IntField()
    words = IntField()
    line = IntField()

    meta = {
        'collection': 'path_entry',
        'indexes': [{'fields': ['path', 'service_links'], 'unique': True}]
    }

    def to_dict(self):
        return {
            'id': str(self.id),
            'path': self.path,
            'status': self.status,
            'size': self.size,
            'words': self.words,
            'line': self.line,
            'service_links_id': str(self.service_links.id) if self.service_links else None
        }

    @classmethod
    def get_or_create(cls, path, service_links, **kwargs):
        existing = cls.objects(path=path, service_links=service_links).first()
        if existing:
            return existing
        instance = cls(path=path, service_links=service_links, **kwargs)
        instance.save()
        return instance
