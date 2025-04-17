use indexmap::IndexMap;

use crate::tokenizer::Kind;

pub struct Spec {
    pub actions: Vec<IndexMap<Kind, Action>>,
    pub goto: Vec<IndexMap<String, usize>>,
    pub start: String,
    pub inlines: IndexMap<usize, u8>,
    pub production_names: Vec<(String, String)>,
}

#[derive(Debug)]
#[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
pub enum Action {
    Shift(usize),
    Reduce(Reduce),
}

#[derive(Debug)]
#[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
pub struct Reduce {
    /// Index of the production in the associated production array
    pub production_id: usize,

    pub non_term: String,

    /// Number of arguments
    pub cnt: usize,
}

#[cfg(feature = "serde")]
#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct SpecSerializable {
    pub actions: Vec<Vec<(String, Action)>>,
    pub goto: Vec<Vec<(String, usize)>>,
    pub start: String,
    pub inlines: Vec<(usize, u8)>,
    pub production_names: Vec<(String, String)>,
}

#[cfg(feature = "serde")]
impl From<SpecSerializable> for Spec {
    fn from(v: SpecSerializable) -> Spec {
        let actions = v
            .actions
            .into_iter()
            .map(|x| x.into_iter().map(|(k, a)| (get_token_kind(&k), a)))
            .map(IndexMap::from_iter)
            .collect();
        let goto = v.goto.into_iter().map(IndexMap::from_iter).collect();
        let inlines = IndexMap::from_iter(v.inlines);

        Spec {
            actions,
            goto,
            start: v.start,
            inlines,
            production_names: v.production_names,
        }
    }
}

#[cfg(feature = "serde")]
pub(super) fn get_token_kind(token_name: &str) -> Kind {
    use Kind::*;

    match token_name {
        "+" => Add,
        "&" => Ampersand,
        "@" => At,
        ".<" => BackwardLink,
        "}" => CloseBrace,
        "]" => CloseBracket,
        ")" => CloseParen,
        "??" => Coalesce,
        ":" => Colon,
        "," => Comma,
        "++" => Concat,
        "/" => Div,
        "." => Dot,
        "**" => DoubleSplat,
        "=" => Eq,
        "//" => FloorDiv,
        "%" => Modulo,
        "*" => Mul,
        "::" => Namespace,
        "{" => OpenBrace,
        "[" => OpenBracket,
        "(" => OpenParen,
        "|" => Pipe,
        "^" => Pow,
        ";" => Semicolon,
        "-" => Sub,

        "?!=" => DistinctFrom,
        ">=" => GreaterEq,
        "<=" => LessEq,
        "?=" => NotDistinctFrom,
        "!=" => NotEq,
        "<" => Less,
        ">" => Greater,

        "IDENT" => Ident,
        "EOI" | "<$>" => EOI,
        "<e>" => Epsilon,

        "BCONST" => BinStr,
        "FCONST" => FloatConst,
        "ICONST" => IntConst,
        "NFCONST" => DecimalConst,
        "NICONST" => BigIntConst,
        "SCONST" => Str,

        "STARTBLOCK" => StartBlock,
        "STARTEXTENSION" => StartExtension,
        "STARTFRAGMENT" => StartFragment,
        "STARTMIGRATION" => StartMigration,
        "STARTSDLDOCUMENT" => StartSDLDocument,

        "+=" => AddAssign,
        "->" => Arrow,
        ":=" => Assign,
        "-=" => SubAssign,

        "PARAMETER" => Parameter,
        "PARAMETERANDTYPE" => ParameterAndType,
        "SUBSTITUTION" => Substitution,

        "STRINTERPSTART" => StrInterpStart,
        "STRINTERPCONT" => StrInterpCont,
        "STRINTERPEND" => StrInterpEnd,

        _ => {
            let mut token_name = token_name.to_lowercase();

            if let Some(rem) = token_name.strip_prefix("dunder") {
                token_name = format!("__{rem}__");
            }

            let kw = crate::keywords::lookup_all(&token_name)
                .unwrap_or_else(|| panic!("unknown keyword {token_name}"));
            Keyword(kw)
        }
    }
}
