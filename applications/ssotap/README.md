# ssotap

IVOA TAP service for Solar System Objects

## Source Code

* <https://github.com/lsst-sqre/tap-postgres>
* <https://github.com/opencadc/tap>

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| cadc-tap.config.backend | string | `"pg"` | What type of backend? |
| cadc-tap.config.datalinkPayloadUrl | string | `"https://github.com/lsst/sdm_schemas/releases/download/2.6.1/datalink-snippets.zip"` | Datalink payload URL |
| cadc-tap.config.gcsBucket | string | `"async-results.lsst.codes"` | Name of GCS bucket in which to store results |
| cadc-tap.config.gcsBucketType | string | `"GCS"` | GCS bucket type (GCS or S3) |
| cadc-tap.config.gcsBucketUrl | string | `"https://tap-files.lsst.codes"` | Base URL for results stored in GCS bucket |
| cadc-tap.config.jvmMaxHeapSize | string | `"31G"` | Java heap size, which will set the maximum size of the heap. Otherwise Java would determine it based on how much memory is available and black maths. |
| cadc-tap.config.pg.database | string | `"dp03_catalogs"` | Postgres database to connect to |
| cadc-tap.config.pg.host | string | `"usdf-pg-catalogs.slac.stanford.edu:5432"` | Postgres hostname:port to connect to |
| cadc-tap.config.pg.username | string | `"dp03"` | Postgres username to use to connect |
| cadc-tap.config.tapSchemaAddress | string | `"cadc-tap-schema-db:3306"` | Address to a MySQL database containing TAP schema data |
| cadc-tap.config.vaultSecretName | string | `"ssotap"` | Vault secret name: the final key in the vault path |
| cadc-tap.ingress.path | string | `"ssotap"` |  |
| cadc-tap.tapSchema.affinity | object | `{}` | Affinity rules for the TAP schema database pod |
| cadc-tap.tapSchema.image.pullPolicy | string | `"IfNotPresent"` | Pull policy for the TAP schema image |
| cadc-tap.tapSchema.image.repository | string | `"lsstsqre/tap-schema-mock"` | TAP schema image to ue. This must be overridden by each environment with the TAP schema for that environment. |
| cadc-tap.tapSchema.image.tag | string | `"2.6.1"` | Tag of TAP schema image |
| cadc-tap.tapSchema.nodeSelector | object | `{}` | Node selection rules for the TAP schema database pod |
| cadc-tap.tapSchema.podAnnotations | object | `{}` | Annotations for the TAP schema database pod |
| cadc-tap.tapSchema.resources | object | `{}` | Resource limits and requests for the TAP schema database pod |
| cadc-tap.tapSchema.tolerations | list | `[]` | Tolerations for the TAP schema database pod |
| cadc-tap.vaultSecretName | string | `""` | Vault secret name, this is appended to the global path to find the vault secrets associated with this deployment. |
| cloudsql.enabled | bool | `false` | Enable the Cloud SQL Auth Proxy sidecar, used with Cloud SQL databases on Google Cloud |
| cloudsql.image.pullPolicy | string | `"IfNotPresent"` | Pull policy for Cloud SQL Auth Proxy images |
| cloudsql.image.repository | string | `"gcr.io/cloudsql-docker/gce-proxy"` | Cloud SQL Auth Proxy image to use |
| cloudsql.image.tag | string | `"1.35.3"` | Cloud SQL Auth Proxy tag to use |
| cloudsql.instanceConnectionName | string | `""` | Instance connection name for a Cloud SQL PostgreSQL instance |
| cloudsql.resources | object | See `values.yaml` | Resource limits and requests for the Cloud SQL Proxy container |
| cloudsql.serviceAccount | string | None, must be set | The Google service account that has an IAM binding to the `ssotap-uws` |
| global.baseUrl | string | Set by Argo CD | Base URL for the environment |
| global.host | string | Set by Argo CD | Host name for ingress |
| global.vaultSecretsPath | string | Set by Argo CD | Base path for Vault secrets |
