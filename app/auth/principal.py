"""Who is calling: a portal user (Bearer JWT) or a customer system (X-API-Key).

Every /api/v1 route depends on one of the guards here, so role, scope and
suspension rules live in one place and are enforced