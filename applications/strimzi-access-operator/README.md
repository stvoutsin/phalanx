# strimzi-access-operator

Strimzi Access Operator

**Homepage:** <https://strimzi.io>

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| image.pullPolicy | string | `"IfNotPresent"` | Image pull policy |
| image.repository | string | `"ghcr.io/lsst-sqre/kafka-access-operator"` | Image repository |
| image.tag | string | The appVersion of the chart | Tag of the image |
| resources | object | See `values.yaml` | Resource requests and limits for strimzi-access-operator |
| serviceAccount.annotations | object | `{}` | Annotations to add to the service account |
| serviceAccount.create | bool | `true` | Specifies whether a service account should be created. |
| serviceAccount.name | string | `""` |  |
