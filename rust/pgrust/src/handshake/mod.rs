#[derive(Clone, Copy, PartialEq, Eq, Default, Debug)]
pub enum ConnectionSslRequirement {
    /// SSL is disabled, and it is an error to attempt to use it.
    #[default]
    Disable,
    /// SSL is optional, but we prefer to use it.
    Optional,
    /// SSL is required and it is an error to reject it.
    Required,
}

mod client_state_machine;

pub mod client {
    pub use super::client_state_machine::*;
}
