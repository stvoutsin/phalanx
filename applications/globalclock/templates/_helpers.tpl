{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "globalclock.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "globalclock.labels" -}}
helm.sh/chart: {{ include "globalclock.chart" . }}
{{ include "globalclock.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "globalclock.selectorLabels" -}}
app.kubernetes.io/name: "globalclock"
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
