use crate::helpers::quote_name;
use crate::keywords::Keyword;
use crate::position::Span;
use crate::tokenizer::{Kind, Token, Value};

/// A node of the CST tree.
///
/// Warning: allocated in the bumpalo arena, which does not Drop.
/// Any types that do allocation with global allocator (such as String or Vec),
/// must manually drop. This is why Terminal has a special vec arena that does
/// Drop.
#[derive(Debug, Clone, Copy, Default)]
pub enum CSTNode<'a> {
    #[default]
    Empty,
    Terminal(&'a Terminal),
    Production(Production<'a>),
}
#[derive(Clone, Debug)]
pub struct Terminal {
    pub kind: Kind,
    pub text: String,
    pub value: Option<Value>,
    pub span: Span,
    pub(super) is_placeholder: bool,
}

#[derive(Debug, Clone, Copy)]
pub struct Production<'a> {
    pub id: usize,
    pub args: &'a [CSTNode<'a>],

    /// When a production is inlined, its id is saved into the new production
    /// This is needed when matching CST nodes by production id.
    pub inlined_ids: Option<&'a [usize]>,
}

impl std::fmt::Display for Terminal {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        if (self.is_placeholder && self.kind == Kind::Ident) || self.text.is_empty() {
            if let Some(user_friendly) = self.kind.user_friendly_text() {
                return write!(f, "{}", user_friendly);
            }
        }

        match self.kind {
            Kind::Ident => write!(f, "'{}'", &quote_name(&self.text)),
            Kind::Keyword(Keyword(kw)) => write!(f, "keyword '{}'", kw.to_ascii_uppercase()),
            _ => write!(f, "'{}'", self.text),
        }
    }
}

impl Terminal {
    pub fn from_token(token: Token) -> Self {
        Terminal {
            kind: token.kind,
            text: token.text.into(),
            value: token.value,
            span: token.span,
            is_placeholder: false,
        }
    }

    #[cfg(feature = "serde")]
    pub fn from_start_name(start_name: &str) -> Self {
        use super::spec;

        Terminal {
            kind: spec::get_token_kind(start_name),
            text: "".to_string(),
            value: None,
            span: Default::default(),
            is_placeholder: false,
        }
    }
}
