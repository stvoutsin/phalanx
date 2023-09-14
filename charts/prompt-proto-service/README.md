# prompt-proto-service

Prompt Proto Service is an event driven service for processing camera images.  The service runs on knative.

**Homepage:** <https://prompt-proto-service.lsst.io/>

## Source Code

* <https://github.com/lsst-dm/prompt_prototype>

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| additionalVolumeMounts | list | `[]` |  |
| affinity | object | `{}` |  |
| apdb.db | string | `""` |  |
| apdb.ip | string | `""` |  |
| apdb.namespace | string | `""` |  |
| apdb.user | string | `""` |  |
| containerConcurrency | int | `1` |  |
| fullnameOverride | string | `"prompt-proto-service"` | Override the full name for resources (includes the release name) |
| image.pullPolicy | string | `"IfNotPresent"` |  |
| image.repository | string | `"ghcr.io/lsst-dm/prompt-proto-service"` |  |
| image.tag | string | `"latest"` |  |
| imageNotifications.imageTimeout | string | `"120"` |  |
| imageNotifications.kafkaClusterAddress | string | `""` |  |
| imageNotifications.topic | string | `""` |  |
| imagePullSecrets | list | `[]` |  |
| instrument.calibRepo | string | `""` |  |
| instrument.name | string | `""` |  |
| instrument.pipelines | string | `""` |  |
| instrument.skymap | string | `""` |  |
| knative.ephemeralStorageLimit | string | `"20Gi"` |  |
| knative.ephemeralStorageRequest | string | `"8Gi"` |  |
| knative.timeout | int | `900` |  |
| nameOverride | string | `""` | Override the base name for resources |
| namespace | string | `"prompt-proto-service"` |  |
| nodeSelector | object | `{}` |  |
| podAnnotations | object | `{"autoscaling.knative.dev/max-scale":"10","autoscaling.knative.dev/min-scale":"1","autoscaling.knative.dev/target-utilization-percentage":"80","revision":"1"}` | Annotations for the prompt-proto-service pod |
| registry.db | string | `"lsstdb1"` |  |
| registry.ip | string | `"usdf-butler.slac.stanford.edu:5432"` |  |
| registry.user | string | `"rubin"` |  |
| s3.auth_env | bool | `true` |  |
| s3.endpointUrl | string | `""` |  |
| s3.imageBucket | string | `""` |  |
| tolerations | list | `[]` |  |
| vaultSecretsPath | string | `""` |  |
