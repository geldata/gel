struct GelConfig {
    config: Config,
}

impl GelConfig {
    pub fn new() -> Self {
        Self { config: Config::new() }
    }
}
