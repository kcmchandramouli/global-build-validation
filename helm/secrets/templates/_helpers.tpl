{{- define "gbv_secrets.fullname" -}}
{{- default .Chart.Name .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "imagePullSecret" }}
{{- with .Values.imageCredentials }}
{{- printf "{\"auths\":{\"%s\":{\"username\":\"%s\",\"password\":\"%s\",\"auth\":\"%s\"}}}" .registry .username .password (printf "%s:%s" .username .password | b64enc) | b64enc }}
{{- end }}
{{- end }}
