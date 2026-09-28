terraform {
  required_version = ">= 1.9.0, < 2.0.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "2.38.0"
    }
  }
}

variable "kubeconfig" {
  type = string
}

variable "context" {
  type = string
}

variable "manifest_path" {
  type = string
}

provider "kubernetes" {
  config_path    = var.kubeconfig
  config_context = var.context
}

locals {
  bundle     = jsondecode(file(var.manifest_path))
  namespaces = [for item in local.bundle.items : item if item.kind == "Namespace"]
  resources = {
    for item in local.bundle.items : "${item.kind}/${item.metadata.name}" => item
    if item.kind != "Namespace"
  }
}

resource "kubernetes_namespace_v1" "workspace" {
  metadata {
    name = one(local.namespaces).metadata.name
  }
  lifecycle {
    prevent_destroy = true
  }
}

resource "kubernetes_manifest" "workspace" {
  for_each   = local.resources
  manifest   = each.value
  depends_on = [kubernetes_namespace_v1.workspace]
  lifecycle {
    prevent_destroy = true
    precondition {
      condition     = each.value.kind != "Secret"
      error_message = "Secrets must be provisioned outside this state."
    }
  }
}
