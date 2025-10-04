# gel-config TODO

This TODO is based on analysis of EdgeDB's Python configuration handling code. Items are organized by priority and complexity.

**Key Python Files Referenced:**
- `edgedb/edb/server/tenant.py` - Main tenant configuration management
- `edgedb/edb/server/multitenant.py` - Multi-tenant configuration handling
- `edgedb/edb/server/main.py` - Server startup and configuration loading
- `edgedb/edb/server/args.py` - Command line argument parsing
- `edgedb/edb/server/server.py` - TLS and server configuration
- `edgedb/edb/server/config/` - Configuration module (spec.py, types.py, ops.py)

## High Priority - Core Configuration Infrastructure

### 1. Configuration File Loading and Parsing
- [ ] **TOML Configuration File Support**
  - [ ] Implement TOML file parsing (similar to `edgedb/edb/server/tenant.py` lines 1815-1832)
  - [ ] Support for `cfg::Config` section parsing
  - [ ] Handle nested configuration structures
  - [ ] Validation against configuration schema

- [ ] **JSON Configuration File Support**
  - [ ] Multi-tenant configuration file parsing (similar to `edgedb/edb/server/multitenant.py` lines 181)
  - [ ] Sidechannel configuration loading (similar to `edgedb/edb/server/tenant.py` lines 281-288)
  - [ ] Configuration serialization/deserialization

### 2. Configuration Reloading and File Monitoring
- [ ] **File System Event Monitoring**
  - [ ] Implement file watching for config files (similar to `edgedb/edb/server/tenant.py` lines 694-738)
  - [ ] Support for SIGHUP signal handling (similar to `edgedb/edb/server/main.py` lines 291-311)
  - [ ] Configurable reload triggers (similar to `edgedb/edb/server/args.py` lines 144-164)
  - [ ] Debounced reloading to prevent rapid file changes

- [ ] **Configuration Hot Reloading**
  - [ ] Reload TLS certificates and keys
  - [ ] Reload JWT allowlists and revocation lists
  - [ ] Reload readiness state files
  - [ ] Reload multi-tenant configuration
  - [ ] Reload TOML configuration files

## Medium Priority - Security and Authentication

### 3. TLS Certificate Management
- [ ] **TLS Certificate and Key Handling**
  - [ ] PEM certificate file loading (similar to `edgedb/edb/server/server.py` lines 243-244, 271)
  - [ ] Certificate validation and verification
  - [ ] Auto-generation of self-signed certificates
  - [ ] Certificate reloading on file changes
  - [ ] Client CA certificate support for mTLS

### 4. JWT/JWS Key Management
- [ ] **JWT Subject Allowlist**
  - [ ] File-based allowlist loading (similar to `edgedb/edb/server/tenant.py` lines 151-154, 705-724)
  - [ ] In-memory caching of allowlist
  - [ ] Hot reloading of allowlist files
  - [ ] Validation of JWT subject claims

- [ ] **JWT Revocation List**
  - [ ] File-based revocation list loading (similar to `edgedb/edb/server/tenant.py` lines 1640-1682)
  - [ ] In-memory caching of revocation list
  - [ ] Hot reloading of revocation files
  - [ ] Validation of JWT token IDs

- [ ] **JWS Key File Support**
  - [ ] PEM and JSON JWK format support
  - [ ] Key rotation and reloading
  - [ ] SCRAM-over-HTTP signing support

## Medium Priority - Multi-Tenant Support

### 5. Multi-Tenant Configuration
- [ ] **Multi-Tenant Config File Parsing**
  - [ ] JSON-based tenant configuration (similar to `edgedb/edb/server/multitenant.py` lines 52-69)
  - [ ] Tenant-specific configuration overrides
  - [ ] SNI-based tenant routing
  - [ ] Backend DSN per tenant

- [ ] **Tenant Lifecycle Management**
  - [ ] Tenant creation and initialization
  - [ ] Tenant configuration reloading
  - [ ] Tenant destruction and cleanup
  - [ ] Admin tenant support

## Medium Priority - Server State Management

### 6. Readiness State Management
- [ ] **Readiness State Files**
  - [ ] File-based readiness state (similar to `edgedb/edb/server/tenant.py` lines 137-138, 1697-1741)
  - [ ] State validation and parsing
  - [ ] Hot reloading of readiness state
  - [ ] Integration with health checks

- [ ] **Readiness State Types**
  - [ ] Default (ready)
  - [ ] Not ready (maintenance)
  - [ ] Read only
  - [ ] Offline
  - [ ] Blocked

### 7. Extension Package Management
- [ ] **Extension Directory Support**
  - [ ] Extension package discovery (similar to `edgedb/edb/server/tenant.py` lines 596-694)
  - [ ] MANIFEST.toml parsing
  - [ ] Extension loading and validation
  - [ ] Extension package caching

## Low Priority - Advanced Features

### 8. Environment Variable Support
- [ ] **Environment Variable Resolution**
  - [ ] Legacy EDGEDB_ prefix support (similar to `edgedb/edb/server/args.py` lines 600-640)
  - [ ] GEL_ prefix support
  - [ ] File-based environment variable loading
  - [ ] Environment variable validation

### 9. Configuration Validation and Error Handling
- [ ] **Configuration Schema Validation**
  - [ ] Type checking for configuration values
  - [ ] Required field validation
  - [ ] Enum value validation
  - [ ] Custom validation rules

- [ ] **Error Handling and Reporting**
  - [ ] Detailed error messages for configuration issues
  - [ ] Graceful fallbacks for missing files
  - [ ] Configuration error logging
  - [ ] Recovery mechanisms

### 10. Configuration Serialization
- [ ] **Configuration Export/Import**
  - [ ] Configuration serialization to JSON
  - [ ] Configuration serialization to TOML
  - [ ] Configuration diffing
  - [ ] Configuration migration support

## Integration Tasks

### 11. Python Integration
- [ ] **Python Bindings**
  - [ ] PyO3 integration for Python calls
  - [ ] Configuration object exposure to Python
  - [ ] Event callbacks for configuration changes
  - [ ] Python exception handling

### 12. Testing Infrastructure
- [ ] **Unit Tests**
  - [ ] Configuration file parsing tests
  - [ ] File monitoring tests
  - [ ] Reload mechanism tests
  - [ ] Error handling tests

- [ ] **Integration Tests**
  - [ ] End-to-end configuration loading tests
  - [ ] Multi-tenant configuration tests
  - [ ] TLS certificate management tests
  - [ ] JWT key management tests

## Documentation Tasks

### 13. Documentation
- [ ] **API Documentation**
  - [ ] Rust API documentation
  - [ ] Python binding documentation
  - [ ] Configuration file format documentation
  - [ ] Examples and tutorials

- [ ] **Migration Guide**
  - [ ] Migration from Python configuration handling
  - [ ] Configuration file format changes
  - [ ] Breaking changes documentation

## Performance and Optimization

### 14. Performance Optimization
- [ ] **Caching and Memory Management**
  - [ ] Configuration value caching
  - [ ] File content caching with invalidation
  - [ ] Memory usage optimization
  - [ ] Lazy loading of configuration sections

- [ ] **Concurrency and Threading**
  - [ ] Thread-safe configuration access
  - [ ] Async file monitoring
  - [ ] Concurrent configuration reloading
  - [ ] Lock-free configuration updates

## Notes

- Priority is based on core functionality needed for EdgeDB server operation
- Each item should include proper error handling and logging
- Consider backward compatibility with existing Python configuration handling
- Focus on performance and memory efficiency for production use
- Ensure thread safety for concurrent access patterns 