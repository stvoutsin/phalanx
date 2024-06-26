{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "rubintv.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "rubintv.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "rubintv.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "rubintv.labels" -}}
app.kubernetes.io/name: {{ include "rubintv.name" . }}
helm.sh/chart: {{ include "rubintv.chart" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "rubintv.workers.labels" -}}
app.kubernetes.io/name: {{ include "rubintv.name" . }}
helm.sh/chart: {{ include "rubintv.chart" . }}
app.kubernetes.io/instance: {{ .Release.Name }}-worker
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "rubintv.selectorLabels" -}}
app.kubernetes.io/name: {{ include "rubintv.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "rubintv.workers.selectorLabels" -}}
app.kubernetes.io/name: {{ include "rubintv.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}-worker
{{- end }}

{{/*
Script name
*/}}
{{- define "rubintv.scriptName" -}}
{{- regexSplit "/" .Values.script.name -1 | last | trimSuffix ".py" | kebabcase }}
{{- end }}
