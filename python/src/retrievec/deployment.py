"""Render an optional single-node Kubernetes deployment without embedding secrets."""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


def render(*, image, origin, issuer, namespace="retrievec", storage_class="local-path"):
    if not re.fullmatch(r"[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?", namespace):
        raise ValueError("invalid namespace")
    if not re.fullmatch(r"[^\s]+@sha256:[a-f0-9]{64}", image):
        raise ValueError("workspace image must be pinned by sha256 digest")
    from retrievec.app.config import Settings

    Settings(dsn="unused", origin=origin, issuer=issuer)
    if not storage_class or len(storage_class) > 253:
        raise ValueError("explicit storage class required")

    def resource(kind, name, *, api="v1", **fields):
        return {
            "apiVersion": api,
            "kind": kind,
            "metadata": {"name": name, "namespace": namespace},
            **fields,
        }

    labels = {"app.kubernetes.io/name": "retrievec"}
    postgres = {"app.kubernetes.io/name": "retrievec-postgres"}
    security = {
        "allowPrivilegeEscalation": False,
        "readOnlyRootFilesystem": True,
        "capabilities": {"drop": ["ALL"]},
    }
    items = [{"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": namespace}}]
    for name, size in (("artifacts", "20Gi"), ("model-cache", "10Gi"), ("registry", "10Gi")):
        items.append(
            resource(
                "PersistentVolumeClaim",
                name,
                spec={
                    "accessModes": ["ReadWriteOnce"],
                    "storageClassName": storage_class,
                    "resources": {"requests": {"storage": size}},
                },
            )
        )
    items.append(
        resource(
            "ConfigMap",
            "workspace",
            data={
                "RETRIEVEC_ORIGIN": origin,
                "RETRIEVEC_OIDC_ISSUER": issuer,
                "RETRIEVEC_OIDC_CLIENT": "retrievec",
                "RETRIEVEC_PRINCIPAL": "*",
                "RETRIEVEC_LOCAL_HTTP": "0",
            },
        )
    )
    items.append(
        resource(
            "Deployment",
            "workspace",
            api="apps/v1",
            spec={
                "replicas": 1,
                "strategy": {"type": "Recreate"},
                "selector": {"matchLabels": labels},
                "template": {
                    "metadata": {"labels": labels},
                    "spec": {
                        "automountServiceAccountToken": False,
                        "terminationGracePeriodSeconds": 45,
                        "securityContext": {
                            "runAsNonRoot": True,
                            "runAsUser": 10001,
                            "runAsGroup": 10001,
                            "fsGroup": 10001,
                            "seccompProfile": {"type": "RuntimeDefault"},
                        },
                        "containers": [
                            {
                                "name": "workspace",
                                "image": image,
                                "args": ["workspace"],
                                "securityContext": security,
                                "envFrom": [
                                    {"configMapRef": {"name": "workspace"}},
                                    {"secretRef": {"name": "workspace-secrets"}},
                                ],
                                "ports": [{"name": "http", "containerPort": 8000}],
                                "resources": {
                                    "requests": {"cpu": "1", "memory": "2Gi"},
                                    "limits": {"cpu": "4", "memory": "6Gi"},
                                },
                                "startupProbe": {
                                    "httpGet": {"path": "/healthz", "port": "http"},
                                    "periodSeconds": 5,
                                    "failureThreshold": 60,
                                },
                                "livenessProbe": {
                                    "httpGet": {"path": "/healthz", "port": "http"},
                                    "periodSeconds": 15,
                                    "timeoutSeconds": 2,
                                },
                                "readinessProbe": {
                                    "httpGet": {"path": "/readyz", "port": "http"},
                                    "periodSeconds": 10,
                                    "timeoutSeconds": 5,
                                },
                                "volumeMounts": [
                                    {"name": "artifacts", "mountPath": "/app/artifacts/store"},
                                    {"name": "model-cache", "mountPath": "/app/artifacts/cache"},
                                    {"name": "temporary", "mountPath": "/tmp"},
                                ],
                            }
                        ],
                        "volumes": [
                            {"name": name, "persistentVolumeClaim": {"claimName": name}}
                            for name in ("artifacts", "model-cache")
                        ]
                        + [{"name": "temporary", "emptyDir": {"sizeLimit": "512Mi"}}],
                    },
                },
            },
        )
    )
    items.append(
        resource(
            "Service",
            "workspace",
            spec={
                "selector": labels,
                "ports": [{"name": "http", "port": 8000, "targetPort": "http"}],
            },
        )
    )
    items.append(
        resource(
            "Service",
            "postgres",
            spec={
                "selector": postgres,
                "ports": [{"name": "postgres", "port": 5432, "targetPort": 5432}],
            },
        )
    )
    items.append(
        resource(
            "Deployment",
            "postgres",
            api="apps/v1",
            spec={
                "replicas": 1,
                "strategy": {"type": "Recreate"},
                "selector": {"matchLabels": postgres},
                "template": {
                    "metadata": {"labels": postgres},
                    "spec": {
                        "automountServiceAccountToken": False,
                        "terminationGracePeriodSeconds": 60,
                        "securityContext": {
                            "runAsUser": 999,
                            "runAsGroup": 999,
                            "runAsNonRoot": True,
                            "fsGroup": 999,
                            "seccompProfile": {"type": "RuntimeDefault"},
                        },
                        "containers": [
                            {
                                "name": "postgres",
                                "image": "postgres:18.3-bookworm",
                                "securityContext": security,
                                "env": [
                                    {"name": "POSTGRES_DB", "value": "retrievec"},
                                    {"name": "POSTGRES_USER", "value": "retrievec"},
                                    {
                                        "name": "POSTGRES_PASSWORD",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": "database-secrets",
                                                "key": "password",
                                            }
                                        },
                                    },
                                ],
                                "resources": {
                                    "requests": {"cpu": "500m", "memory": "256Mi"},
                                    "limits": {"memory": "1Gi"},
                                },
                                "readinessProbe": {
                                    "exec": {
                                        "command": [
                                            "pg_isready",
                                            "-U",
                                            "retrievec",
                                            "-d",
                                            "retrievec",
                                        ]
                                    }
                                },
                                "volumeMounts": [
                                    {"name": "registry", "mountPath": "/var/lib/postgresql"},
                                    {"name": "socket", "mountPath": "/var/run/postgresql"},
                                    {"name": "temporary", "mountPath": "/tmp"},
                                ],
                            }
                        ],
                        "volumes": [
                            {
                                "name": "registry",
                                "persistentVolumeClaim": {"claimName": "registry"},
                            },
                            {"name": "socket", "emptyDir": {}},
                            {"name": "temporary", "emptyDir": {}},
                        ],
                    },
                },
            },
        )
    )
    items.append(
        resource(
            "NetworkPolicy",
            "default-deny",
            api="networking.k8s.io/v1",
            spec={"podSelector": {}, "policyTypes": ["Ingress", "Egress"]},
        )
    )
    items.append(
        resource(
            "NetworkPolicy",
            "database",
            api="networking.k8s.io/v1",
            spec={
                "podSelector": {"matchLabels": postgres},
                "policyTypes": ["Ingress"],
                "ingress": [
                    {
                        "from": [{"podSelector": {"matchLabels": labels}}],
                        "ports": [{"port": 5432, "protocol": "TCP"}],
                    }
                ],
            },
        )
    )
    items.append(
        resource(
            "NetworkPolicy",
            "workspace",
            api="networking.k8s.io/v1",
            spec={
                "podSelector": {"matchLabels": labels},
                "policyTypes": ["Ingress", "Egress"],
                "ingress": [
                    {
                        "from": [
                            {"namespaceSelector": {"matchLabels": {"retrievec.io/gateway": "true"}}}
                        ],
                        "ports": [{"port": 8000}],
                    }
                ],
                "egress": [
                    {"to": [{"podSelector": {"matchLabels": postgres}}], "ports": [{"port": 5432}]},
                    {
                        "to": [
                            {
                                "namespaceSelector": {
                                    "matchLabels": {"kubernetes.io/metadata.name": "kube-system"}
                                }
                            }
                        ],
                        "ports": [{"port": 53, "protocol": "UDP"}, {"port": 53, "protocol": "TCP"}],
                    },
                    {"ports": [{"port": 443, "protocol": "TCP"}]},
                ],
            },
        )
    )
    return {"apiVersion": "v1", "kind": "List", "items": items}


def gateway_route(
    origin, namespace="retrievec", gateway="retrievec", gateway_namespace="gateway-system"
):
    host = urlsplit(origin).hostname
    return {
        "apiVersion": "gateway.networking.k8s.io/v1",
        "kind": "HTTPRoute",
        "metadata": {"name": "workspace", "namespace": namespace},
        "spec": {
            "parentRefs": [
                {"name": gateway, "namespace": gateway_namespace, "sectionName": "https"}
            ],
            "hostnames": [host],
            "rules": [{"backendRefs": [{"name": "workspace", "port": 8000}]}],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("image", "origin", "issuer"):
        parser.add_argument("--" + field, required=True)
    parser.add_argument("--namespace", default="retrievec")
    parser.add_argument("--storage-class", default="local-path")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gateway", action="store_true")
    args = parser.parse_args()
    result = render(
        image=args.image,
        origin=args.origin,
        issuer=args.issuer,
        namespace=args.namespace,
        storage_class=args.storage_class,
    )
    if args.gateway:
        result["items"].append(gateway_route(args.origin, args.namespace))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
