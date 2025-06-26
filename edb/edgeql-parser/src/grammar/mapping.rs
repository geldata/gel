use crate::ast;
use crate::grammar::definitions as d;

impl From<d::EdgeQLGrammarArgs> for ast::GrammarEntryPoint {
    fn from(value: d::EdgeQLGrammarArgs) -> Self {
        use d::EdgeQLGrammarArgs::*;

        match value {
            STARTBLOCK_EdgeQLBlock_EOI(_, commands, _) => {
                ast::GrammarEntryPoint::Commands(commands)
            }
            STARTEXTENSION_CreateExtensionPackageCommandsBlock_EOI(_, _, _) => todo!(),

            STARTFRAGMENT_ExprStmt_EOI(_, x, _) => ast::GrammarEntryPoint::Query(x),
            STARTFRAGMENT_Expr_EOI(_, x, _) => ast::GrammarEntryPoint::Expr(Box::new(x)),

            STARTMIGRATION_CreateMigrationCommandsBlock_EOI(..) => todo!(),
            STARTSDLDOCUMENT_SDLDocument_EOI(..) => todo!(),
        }
    }
}

impl From<d::EdgeQLBlockArgs> for ast::Commands {
    fn from(value: d::EdgeQLBlockArgs) -> Self {
        use d::EdgeQLBlockArgs::*;

        match value {
            OptSemicolons(_) => ast::Commands { commands: vec![] },
            StatementBlock_OptSemicolons(commands, _) => ast::Commands { commands },
        }
    }
}

impl From<d::SingleStatementArgs> for ast::Command {
    fn from(value: d::SingleStatementArgs) -> Self {
        use d::SingleStatementArgs::*;

        match value {
            ConfigStmt(_) => todo!(),
            DDLStmt(_) => todo!(),
            IfThenElseExpr(_) => todo!(),
            SessionStmt(_) => todo!(),
            Stmt(s) => s,
        }
    }
}

impl From<d::StmtArgs> for ast::Command {
    fn from(value: d::StmtArgs) -> Self {
        use d::StmtArgs::*;

        match value {
            AdministerStmt(_) => todo!(),
            AnalyzeStmt(_) => todo!(),
            DescribeStmt(_) => todo!(),
            ExprStmt(q) => ast::Command::Query(q),
            TransactionStmt(_) => todo!(),
        }
    }
}

impl From<d::ExprStmtArgs> for ast::Query {
    fn from(value: d::ExprStmtArgs) -> Self {
        use d::ExprStmtArgs::*;

        match value {
            ExprStmtAnnoying(_) => todo!(),
            ExprStmtSimple(q) => q,
        }
    }
}

impl From<d::ExprStmtSimpleArgs> for ast::Query {
    fn from(value: d::ExprStmtSimpleArgs) -> Self {
        use d::ExprStmtSimpleArgs::*;

        match value {
            ExprStmtSimpleCore(e) => e,
            WithBlock_ExprStmtSimpleCore(_, _) => todo!(),
        }
    }
}

impl From<d::ExprStmtSimpleCoreArgs> for ast::Query {
    fn from(value: d::ExprStmtSimpleCoreArgs) -> Self {
        use d::ExprStmtSimpleCoreArgs::*;

        match value {
            InternalGroup(_) => todo!(),
            SimpleDelete(_) => todo!(),
            SimpleFor(_) => todo!(),
            SimpleInsert(_) => todo!(),
            SimpleSelect(q) => ast::Query::SelectQuery(q),
            SimpleUpdate(_) => todo!(),
        }
    }
}

impl From<d::SimpleSelectArgs> for ast::SelectQuery {
    fn from(value: d::SimpleSelectArgs) -> Self {
        use d::SimpleSelectArgs::*;

        match value {
            SELECT_OptionallyAliasedExpr_OptFilterClause_OptSortClause_OptSelectLimit(
                _,
                (alias, result),
                r#where,
                orderby,
                (offset, limit),
            ) => {
                let result = Box::new(result);
                let r#where = r#where.map(Box::new);
                let orderby = Some(orderby);
                let offset = offset.map(Box::new);
                let limit = limit.map(Box::new);

                if offset.is_some() || limit.is_some() {
                    let subj = ast::Expr::Query(ast::Query::SelectQuery(ast::SelectQuery {
                        result,
                        result_alias: alias,
                        r#where,
                        orderby,
                        implicit: true,

                        aliases: None,
                        offset: None,
                        limit: None,
                        rptr_passthrough: false,
                        // span=merge_spans((kids[0], kids[3]))
                    }));

                    ast::SelectQuery {
                        result: Box::new(subj),
                        offset,
                        limit,

                        orderby: None,
                        result_alias: None,
                        r#where: None,
                        aliases: None,
                        rptr_passthrough: false,
                        implicit: false,
                    }
                } else {
                    ast::SelectQuery {
                        result,
                        result_alias: alias,
                        r#where,
                        orderby,

                        aliases: None,
                        offset: None,
                        limit: None,
                        rptr_passthrough: false,
                        implicit: false,
                    }
                }
            }
        }
    }
}

impl From<d::OptionallyAliasedExprArgs> for (Option<String>, ast::Expr) {
    fn from(value: d::OptionallyAliasedExprArgs) -> Self {
        use d::OptionallyAliasedExprArgs::*;

        match value {
            AliasedExpr(a) => (Some(a.alias), *a.expr),
            Expr(e) => (None, e),
        }
    }
}

impl From<d::AliasedExprArgs> for ast::AliasedExpr {
    fn from(value: d::AliasedExprArgs) -> Self {
        use d::AliasedExprArgs::*;

        match value {
            Identifier_ASSIGN_Expr(alias, _, expr) => ast::AliasedExpr {
                alias,
                expr: Box::new(expr),
            },
        }
    }
}

// edgeql_parser_derive::list! { ExprList, GenExpr, ast::Expr, COMMA, true }

impl From<d::GenExprArgs> for ast::Expr {
    fn from(value: d::GenExprArgs) -> Self {
        match value {
            d::GenExprArgs::Expr(e) => e,
            d::GenExprArgs::ExprStmtSimpleCore(q) => ast::Expr::Query(q),
        }
    }
}

impl From<d::ExprArgs> for ast::Expr {
    fn from(value: d::ExprArgs) -> Self {
        use d::ExprArgs::*;
        match value {
            BaseAtomicExpr(e) => e,
            DETACHED_Expr(_, e) => ast::Expr::DetachedExpr(ast::DetachedExpr {
                expr: Box::new(e),
                preserve_path_prefix: false,
            }),
            DISTINCT_Expr(..) => todo!(),
            EXISTS_Expr(..) => todo!(),
            Expr_AND_Expr(..) => todo!(),
            Expr_CIRCUMFLEX_Expr(..) => todo!(),
            Expr_CompareOp_Expr_P_COMPARE_OP(..) => todo!(),
            Expr_DOUBLEPLUS_Expr(..) => todo!(),
            Expr_DOUBLEQMARK_Expr_P_DOUBLEQMARK_OP(..) => todo!(),
            Expr_DOUBLESLASH_Expr(..) => todo!(),
            Expr_EXCEPT_Expr(..) => todo!(),
            Expr_IF_Expr_ELSE_Expr(..) => todo!(),
            Expr_ILIKE_Expr(..) => todo!(),
            Expr_INTERSECT_Expr(..) => todo!(),
            Expr_IN_Expr(..) => todo!(),
            Expr_IS_NOT_TypeExpr_P_IS(..) => todo!(),
            Expr_IS_TypeExpr(..) => todo!(),
            Expr_IndirectionEl(..) => todo!(),
            Expr_LIKE_Expr(..) => todo!(),
            Expr_MINUS_Expr(..) => todo!(),
            Expr_NOT_ILIKE_Expr(..) => todo!(),
            Expr_NOT_IN_Expr_P_IN(..) => todo!(),
            Expr_NOT_LIKE_Expr(..) => todo!(),
            Expr_OR_Expr(..) => todo!(),
            Expr_PERCENT_Expr(..) => todo!(),
            Expr_PLUS_Expr(..) => todo!(),
            Expr_SLASH_Expr(..) => todo!(),
            Expr_STAR_Expr(..) => todo!(),
            Expr_Shape(..) => todo!(),
            Expr_UNION_Expr(..) => todo!(),
            GLOBAL_NodeName(..) => todo!(),
            INTROSPECT_TypeExpr(..) => todo!(),
            IfThenElseExpr(..) => todo!(),
            LANGBRACKET_FullTypeExpr_RANGBRACKET_Expr_P_TYPECAST(..) => todo!(),
            LANGBRACKET_OPTIONAL_FullTypeExpr_RANGBRACKET_Expr_P_TYPECAST(..) => todo!(),
            LANGBRACKET_REQUIRED_FullTypeExpr_RANGBRACKET_Expr_P_TYPECAST(..) => todo!(),
            MINUS_Expr_P_UMINUS(..) => todo!(),
            NOT_Expr(..) => todo!(),
            PLUS_Expr_P_UMINUS(..) => todo!(),
            Path(..) => todo!(),
        }
    }
}

impl From<d::BaseAtomicExprArgs> for ast::Expr {
    fn from(value: d::BaseAtomicExprArgs) -> Self {
        use d::BaseAtomicExprArgs::*;
        match value {
            Collection(_) => todo!(),
            Constant(c) => c,
            DUNDERDEFAULT(..) => ast::Expr::Anchor(ast::Anchor::IRAnchor(ast::IRAnchor {
                name: "__default__".into(),
                has_dml: false,
                move_scope: false,
            })),
            DUNDERNEW(..) => ast::Expr::Anchor(ast::Anchor::IRAnchor(ast::IRAnchor {
                name: "__new__".into(),
                has_dml: false,
                move_scope: false,
            })),
            DUNDEROLD(..) => ast::Expr::Anchor(ast::Anchor::IRAnchor(ast::IRAnchor {
                name: "__old__".into(),
                has_dml: false,
                move_scope: false,
            })),
            DUNDERSOURCE(..) => ast::Expr::Anchor(ast::Anchor::IRAnchor(ast::IRAnchor {
                name: "__source__".into(),
                has_dml: false,
                move_scope: false,
            })),
            DUNDERSPECIFIED(..) => ast::Expr::Anchor(ast::Anchor::IRAnchor(ast::IRAnchor {
                name: "__specified__".into(),
                has_dml: false,
                move_scope: false,
            })),
            DUNDERSUBJECT(..) => ast::Expr::Anchor(ast::Anchor::IRAnchor(ast::IRAnchor {
                name: "__subject__".into(),
                has_dml: false,
                move_scope: false,
            })),
            FreeShape(_) => todo!(),
            FuncExpr(_) => todo!(),
            NamedTuple(_) => todo!(),
            NodeName_P_DOT(..) => todo!(),
            ParenExpr_P_UMINUS(..) => todo!(),
            PathStep_P_DOT(..) => todo!(),
            Set(..) => todo!(),
            StringInterpolation(..) => todo!(),
            Tuple(..) => todo!(),
        }
    }
}

impl From<d::ConstantArgs> for ast::Expr {
    fn from(value: d::ConstantArgs) -> Self {
        match value {
            d::ConstantArgs::BaseBooleanConstant(c)
            | d::ConstantArgs::BaseNumberConstant(c)
            | d::ConstantArgs::BaseStringConstant(c) => {
                ast::Expr::BaseConstant(ast::BaseConstant::Constant(c))
            }
            d::ConstantArgs::BaseBytesConstant(c) => ast::Expr::BaseConstant(c),
            d::ConstantArgs::PARAMETER(t) => ast::Expr::Parameter(ast::Parameter {
                name: t.text[1..].to_string(),
                is_func_param: false,
            }),
            d::ConstantArgs::PARAMETERANDTYPE(t) => {
                let t: crate::parser::Terminal = t;

                assert!(t.text.starts_with("<lit "));

                let (type_name, param_name) = t
                    .text
                    .strip_prefix("<lit ")
                    .unwrap()
                    .split_once(">$")
                    .unwrap();

                ast::Expr::TypeCast(ast::TypeCast {
                    r#type: ast::TypeExpr::TypeName(ast::TypeName {
                        name: None,
                        maintype: ast::BaseObjectRef::ObjectRef(ast::ObjectRef {
                            name: type_name.into(),
                            module: Some("__std__".into()),
                            itemclass: None,
                        }),
                        subtypes: None,
                        dimensions: None,
                        // span: param.span,
                    }),
                    expr: Box::new(ast::Expr::Parameter(ast::Parameter {
                        name: param_name.into(),
                        is_func_param: false,
                        // span=param.span,
                    })),
                    cardinality_mod: None,
                })
            }
        }
    }
}

impl From<d::BaseBooleanConstantArgs> for ast::Constant {
    fn from(value: d::BaseBooleanConstantArgs) -> Self {
        match value {
            d::BaseBooleanConstantArgs::FALSE(..) => ast::Constant {
                kind: ast::ConstantKind::BOOLEAN,
                value: "false".into(),
            },
            d::BaseBooleanConstantArgs::TRUE(..) => ast::Constant {
                kind: ast::ConstantKind::BOOLEAN,
                value: "true".into(),
            },
        }
    }
}

impl From<d::BaseBytesConstantArgs> for ast::BaseConstant {
    fn from(value: d::BaseBytesConstantArgs) -> Self {
        match value {
            d::BaseBytesConstantArgs::BCONST(t) => {
                let Some(crate::tokenizer::Value::Bytes(value)) = t.value else {
                    panic!()
                };
                ast::BaseConstant::BytesConstant(ast::BytesConstant { value })
            }
        }
    }
}

impl From<d::BaseNumberConstantArgs> for ast::Constant {
    fn from(value: d::BaseNumberConstantArgs) -> Self {
        use d::BaseNumberConstantArgs::*;
        match value {
            FCONST(t) => ast::Constant {
                kind: ast::ConstantKind::FLOAT,
                value: t.text,
            },
            ICONST(t) => ast::Constant {
                kind: ast::ConstantKind::INTEGER,
                value: t.text,
            },
            NFCONST(t) => ast::Constant {
                kind: ast::ConstantKind::DECIMAL,
                value: t.text,
            },
            NICONST(t) => ast::Constant {
                kind: ast::ConstantKind::BIGINT,
                value: t.text,
            },
        }
    }
}

impl From<d::BaseStringConstantArgs> for ast::Constant {
    fn from(value: d::BaseStringConstantArgs) -> Self {
        match value {
            d::BaseStringConstantArgs::SCONST(t) => ast::Constant {
                kind: ast::ConstantKind::STRING,
                value: t.text,
            },
        }
    }
}

impl From<d::OptFilterClauseArgs> for Option<ast::Expr> {
    fn from(value: d::OptFilterClauseArgs) -> Self {
        use d::OptFilterClauseArgs::*;

        match value {
            FilterClause(x) => Some(x),
            epsilon() => None,
        }
    }
}

impl From<d::FilterClauseArgs> for ast::Expr {
    fn from(value: d::FilterClauseArgs) -> Self {
        use d::FilterClauseArgs::*;

        match value {
            FILTER_Expr(_, e) => e,
        }
    }
}

impl From<d::OptSortClauseArgs> for Vec<ast::SortExpr> {
    fn from(value: d::OptSortClauseArgs) -> Self {
        use d::OptSortClauseArgs::*;

        match value {
            SortClause(c) => c,
            epsilon() => vec![],
        }
    }
}

impl From<d::SortClauseArgs> for Vec<ast::SortExpr> {
    fn from(value: d::SortClauseArgs) -> Self {
        use d::SortClauseArgs::*;

        match value {
            ORDERBY_OrderbyList(_, c) => c,
        }
    }
}

impl From<d::OptSelectLimitArgs> for (Option<ast::Expr>, Option<ast::Expr>) {
    fn from(value: d::OptSelectLimitArgs) -> Self {
        use d::OptSelectLimitArgs::*;

        match value {
            SelectLimit(s) => s,
            epsilon() => (None, None),
        }
    }
}

impl From<d::SelectLimitArgs> for (Option<ast::Expr>, Option<ast::Expr>) {
    fn from(value: d::SelectLimitArgs) -> Self {
        use d::SelectLimitArgs::*;

        match value {
            LimitClause(l) => (None, Some(l)),
            OffsetClause(o) => (Some(o), None),
            OffsetClause_LimitClause(o, l) => (Some(o), Some(l)),
        }
    }
}

impl From<d::AccessKindArgs> for Vec<ast::AccessKind> {
    fn from(value: d::AccessKindArgs) -> Self {
        use ast::AccessKind::*;
        use d::AccessKindArgs::*;
        match value {
            ALL(_) => vec![Delete, Insert, Select, UpdateRead, UpdateWrite],
            DELETE(_) => vec![Delete],
            INSERT(_) => vec![Insert],
            SELECT(_) => vec![Select],
            UPDATE(_) => vec![UpdateRead, UpdateWrite],
            UPDATE_READ(..) => vec![UpdateRead],
            UPDATE_WRITE(..) => vec![UpdateWrite],
        }
    }
}
