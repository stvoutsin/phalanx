.. px-app:: ssotap

#####################################################
ssotap — IVOA DP03 Solar System Table Access Protocol
#####################################################

SSOTAP (SSO Table Access Protocol) is an IVOA_ service that provides access to the ObsCore table which is hosted on postgres.
On the Rubin Science Platform, it is provided by `tap-postgres <https://github.com/lsst-sqre/tap-postgres>`__, which is derived from the `CADC TAP service <https://github.com/opencadc/tap>`__.
This service provides access to the Solar System tables that are created and served by the butler.

The TAP data itself, apart from schema queries, comes from Postgres.
The TAP schema is provided by images built from the `sdm_schemas <https://github.com/lsst/sdm_schemas/>`__ repository.

.. jinja:: tap
   :file: applications/_summary.rst.jinja

Guides
======

.. toctree::

   values
