use gel_jwt::{Key, KeyRegistry};
use gel_stream::{ResolvedTarget, TlsKey};

mod python;

pub enum ReloadTrigger {
    Default,
    Never,
    Signal,
    FileSystemEvent,
}

pub enum KeyMode {
    Generate,
    Require,
    Optional,
}

pub enum ReadinessState {
    NotReady,
    Ready,
    Maintenance,
}

/// Collection of all file paths that the EdgeDB server reads from disk or external sources
/// for configuration loading, key loading, and file reload checks.
pub struct GelConfigPaths {
    /// Trigger for file system event reloading.
    pub reload_trigger: ReloadTrigger,

    /// Mode for TLS key loading.
    pub tls_mode: KeyMode,

    /// PEM format certificate file containing server certificate and possibly CA certificates.
    /// Can be auto-generated if TLS cert mode is set to generate_self_signed.
    pub tls_cert_file: Option<std::path::PathBuf>,
    
    /// PEM format private key file for TLS. Can be password-protected.
    /// Can be auto-generated if TLS cert mode is set to generate_self_signed.
    pub tls_key_file: Option<std::path::PathBuf>,
    
    /// CA certificate file for client certificate verification (mTLS).
    pub tls_client_ca_file: Option<std::path::PathBuf>,
    
    /// Password for the TLS private key file.
    pub tls_key_password: Option<String>,

    /// Mode for JWT key loading.
    pub jwt_mode: KeyMode,

    /// PEM or JSON JWK format file for JWT signature verification and SCRAM-over-HTTP signing.
    /// Can be auto-generated if JOSE key mode is set to generate.
    pub jws_key_file: Option<std::path::PathBuf>,
    
    /// Text file containing one JWT "sub" claim value per line.
    /// Controls which JWT subjects are allowed access.
    pub jwt_sub_allowlist_file: Option<std::path::PathBuf>,
    
    /// Text file containing one JWT "jti" claim value per line.
    /// Controls which JWT tokens are revoked.
    pub jwt_revocation_list_file: Option<std::path::PathBuf>,
    
    /// TOML format configuration file containing cfg::Config section with server settings.
    /// Can include magic_smtp_config section.
    pub config_file: Option<std::path::PathBuf>,
    
    /// JSON format file defining multiple tenants for multi-tenant mode.
    /// Each tenant has SNI name, backend DSN, and tenant-specific configs.
    pub multitenant_config_file: Option<std::path::PathBuf>,
    
    // Readiness State Files
    /// Text file containing server readiness state in format "state:reason".
    /// Controls whether server accepts connections (e.g., "not_ready:maintenance").
    pub readiness_state_file: Option<std::path::PathBuf>,
    
    // Extension Package Files
    /// Directories containing extension packages, each with a MANIFEST.toml file.
    pub extensions_dirs: Vec<std::path::PathBuf>,
}

pub struct GelTenantConfig {

    // TenantConfig = TypedDict(
    //     "TenantConfig",
    //     {
    //         "instance-name": str,
    //         "backend-dsn": str,
    //         "max-backend-connections": int,
    //         "tenant-id": str,
    //         "backend-adaptive-ha": bool,
    //         "jwt-sub-allowlist-file": str,
    //         "jwt-revocation-list-file": str,
    //         "readiness-state-file": str,
    //         "admin": bool,
    //         "config-file": str,
    //     },
    // )
    
}

pub enum GelConfigItemUpdate<T> {
    Changed(T),
    Unchanged(T),
}

/// Whenever the configuration files are updated, this struct is broadcast to
/// all listeners.
pub struct GelConfigUpdate {
    pub listen_addresses: GelConfigItemUpdate<Vec<ResolvedTarget>>,
    pub instance_name: GelConfigItemUpdate<String>,
    pub backend_dsn: GelConfigItemUpdate<String>,
    pub max_backend_connections: GelConfigItemUpdate<u32>,
    pub backend_adaptive_ha: GelConfigItemUpdate<bool>,
    pub admin_enabled: GelConfigItemUpdate<bool>,
    pub tls_cert_file: GelConfigItemUpdate<TlsKey>,
    pub jwt_keys: GelConfigItemUpdate<KeyRegistry<Key>>,
    pub extensions_dirs: GelConfigItemUpdate<Vec<std::path::PathBuf>>,
    pub readiness_state: GelConfigItemUpdate<ReadinessState>,
}

pub enum GelTenantUpdate {
    Created(String, GelTenantConfig),
    Modified(Option<String>, GelTenantConfig),
    Deleted(String),
}

pub struct GelConfig {
    paths: GelConfigPaths,
    tenant_config: GelTenantConfig,
    update: GelConfigUpdate,
}
