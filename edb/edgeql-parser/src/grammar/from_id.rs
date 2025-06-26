// DO NOT EDIT. This file was generated with:
//
// $ edb gen-rust-ast

impl super::FromId for super::AbortMigrationStmt {
    fn from_id(id: usize) -> Self {
        match id {
            0 => Self::ABORT_MIGRATION,
            1 => Self::ABORT_MIGRATION_REWRITE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AccessKind {
    fn from_id(id: usize) -> Self {
        match id {
            2 => Self::ALL,
            3 => Self::DELETE,
            4 => Self::INSERT,
            5 => Self::SELECT,
            6 => Self::UPDATE,
            7 => Self::UPDATE_READ,
            8 => Self::UPDATE_WRITE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AccessKindList {
    fn from_id(id: usize) -> Self {
        match id {
            9 => Self::AccessKind,
            10 => Self::AccessKindList_COMMA_AccessKind,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AccessPermStmt {
    fn from_id(id: usize) -> Self {
        match id {
            11 => Self::AccessPolicyAction_AccessKindList,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AccessPolicyAction {
    fn from_id(id: usize) -> Self {
        match id {
            12 => Self::ALLOW,
            13 => Self::DENY,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AccessPolicyDeclarationBlock {
    fn from_id(id: usize) -> Self {
        match id {
            14 => Self::ACCESS_POLICY_ShortNodeName_OptWhenBlock_AccessPolicyAction_AccessKindList_OptUsingBlock_CreateAccessPolicySDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AccessPolicyDeclarationShort {
    fn from_id(id: usize) -> Self {
        match id {
            15 => Self::ACCESS_POLICY_ShortNodeName_OptWhenBlock_AccessPolicyAction_AccessKindList_OptUsingBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AccessUsingStmt {
    fn from_id(id: usize) -> Self {
        match id {
            16 => Self::RESET_EXPRESSION,
            17 => Self::USING_ParenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AccessWhenStmt {
    fn from_id(id: usize) -> Self {
        match id {
            18 => Self::RESET_WHEN,
            19 => Self::WHEN_ParenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AdministerStmt {
    fn from_id(id: usize) -> Self {
        match id {
            20 => Self::ADMINISTER_FuncExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AliasDecl {
    fn from_id(id: usize) -> Self {
        match id {
            21 => Self::AliasedExpr,
            22 => Self::Identifier_ASSIGN_ExprStmtSimple,
            23 => Self::Identifier_AS_MODULE_ModuleName,
            24 => Self::MODULE_ModuleName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AliasDeclaration {
    fn from_id(id: usize) -> Self {
        match id {
            25 => Self::ALIAS_NodeName_CreateAliasSDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AliasDeclarationShort {
    fn from_id(id: usize) -> Self {
        match id {
            26 => Self::ALIAS_NodeName_CreateAliasSingleSDLCommandBlock,
            27 => Self::ALIAS_NodeName_ASSIGN_GenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AliasedExpr {
    fn from_id(id: usize) -> Self {
        match id {
            28 => Self::Identifier_ASSIGN_Expr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AliasedExprList {
    fn from_id(id: usize) -> Self {
        match id {
            29 => Self::AliasedExprListInner,
            30 => Self::AliasedExprListInner_COMMA,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AliasedExprListInner {
    fn from_id(id: usize) -> Self {
        match id {
            31 => Self::AliasedExpr,
            32 => Self::AliasedExprListInner_COMMA_AliasedExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterAbstract {
    fn from_id(id: usize) -> Self {
        match id {
            33 => Self::DROP_ABSTRACT,
            34 => Self::RESET_ABSTRACT,
            35 => Self::SET_ABSTRACT,
            36 => Self::SET_NOT_ABSTRACT,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterAccessPolicyCommand {
    fn from_id(id: usize) -> Self {
        match id {
            37 => Self::AccessPermStmt,
            38 => Self::AccessUsingStmt,
            39 => Self::AccessWhenStmt,
            40 => Self::AlterAnnotationValueStmt,
            41 => Self::CreateAnnotationValueStmt,
            42 => Self::DropAnnotationValueStmt,
            43 => Self::RenameStmt,
            44 => Self::ResetFieldStmt,
            45 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterAccessPolicyCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            46 => Self::AlterAccessPolicyCommand,
            47 => Self::LBRACE_AlterAccessPolicyCommandsList_OptSemicolons_RBRACE,
            48 => Self::LBRACE_OptSemicolons_RBRACE,
            49 => Self::LBRACE_Semicolons_AlterAccessPolicyCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterAccessPolicyCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            50 => Self::AlterAccessPolicyCommand,
            51 => Self::AlterAccessPolicyCommandsList_Semicolons_AlterAccessPolicyCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterAccessPolicyStmt {
    fn from_id(id: usize) -> Self {
        match id {
            52 => Self::ALTER_ACCESS_POLICY_UnqualifiedPointerName_AlterAccessPolicyCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterAliasCommand {
    fn from_id(id: usize) -> Self {
        match id {
            53 => Self::AlterAnnotationValueStmt,
            54 => Self::CreateAnnotationValueStmt,
            55 => Self::DropAnnotationValueStmt,
            56 => Self::RenameStmt,
            57 => Self::ResetFieldStmt,
            58 => Self::SetFieldStmt,
            59 => Self::UsingStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterAliasCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            60 => Self::AlterAliasCommand,
            61 => Self::LBRACE_AlterAliasCommandsList_OptSemicolons_RBRACE,
            62 => Self::LBRACE_OptSemicolons_RBRACE,
            63 => Self::LBRACE_Semicolons_AlterAliasCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterAliasCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            64 => Self::AlterAliasCommand,
            65 => Self::AlterAliasCommandsList_Semicolons_AlterAliasCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterAliasStmt {
    fn from_id(id: usize) -> Self {
        match id {
            66 => Self::ALTER_ALIAS_NodeName_AlterAliasCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterAnnotationCommand {
    fn from_id(id: usize) -> Self {
        match id {
            67 => Self::AlterAnnotationValueStmt,
            68 => Self::CreateAnnotationValueStmt,
            69 => Self::DropAnnotationValueStmt,
            70 => Self::RenameStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterAnnotationCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            71 => Self::AlterAnnotationCommand,
            72 => Self::LBRACE_AlterAnnotationCommandsList_OptSemicolons_RBRACE,
            73 => Self::LBRACE_OptSemicolons_RBRACE,
            74 => Self::LBRACE_Semicolons_AlterAnnotationCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterAnnotationCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            75 => Self::AlterAnnotationCommand,
            76 => Self::AlterAnnotationCommandsList_Semicolons_AlterAnnotationCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterAnnotationStmt {
    fn from_id(id: usize) -> Self {
        match id {
            77 => Self::ALTER_ABSTRACT_ANNOTATION_NodeName_AlterAnnotationCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterAnnotationValueStmt {
    fn from_id(id: usize) -> Self {
        match id {
            78 => Self::ALTER_ANNOTATION_NodeName_ASSIGN_GenExpr,
            79 => Self::ALTER_ANNOTATION_NodeName_DROP_OWNED,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterBranchCommand {
    fn from_id(id: usize) -> Self {
        match id {
            80 => Self::RenameStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterBranchCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            81 => Self::AlterBranchCommand,
            82 => Self::LBRACE_AlterBranchCommandsList_OptSemicolons_RBRACE,
            83 => Self::LBRACE_OptSemicolons_RBRACE,
            84 => Self::LBRACE_Semicolons_AlterBranchCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterBranchCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            85 => Self::AlterBranchCommand,
            86 => Self::AlterBranchCommandsList_Semicolons_AlterBranchCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterBranchStmt {
    fn from_id(id: usize) -> Self {
        match id {
            87 => Self::ALTER_BRANCH_DatabaseName_BranchOptions_AlterBranchCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterCastCommand {
    fn from_id(id: usize) -> Self {
        match id {
            88 => Self::AlterAnnotationValueStmt,
            89 => Self::CreateAnnotationValueStmt,
            90 => Self::DropAnnotationValueStmt,
            91 => Self::ResetFieldStmt,
            92 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterCastCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            93 => Self::AlterCastCommand,
            94 => Self::LBRACE_AlterCastCommandsList_OptSemicolons_RBRACE,
            95 => Self::LBRACE_OptSemicolons_RBRACE,
            96 => Self::LBRACE_Semicolons_AlterCastCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterCastCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            97 => Self::AlterCastCommand,
            98 => Self::AlterCastCommandsList_Semicolons_AlterCastCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterCastStmt {
    fn from_id(id: usize) -> Self {
        match id {
            99 => Self::ALTER_CAST_FROM_TypeName_TO_TypeName_AlterCastCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterCommand {
    fn from_id(id: usize) -> Self {
        match id {
            100 => Self::AlterAnnotationValueStmt,
            101 => Self::CreateAnnotationValueStmt,
            102 => Self::DropAnnotationValueStmt,
            103 => Self::RenameStmt,
            104 => Self::ResetFieldStmt,
            105 => Self::SetFieldStmt,
            106 => Self::UsingStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            107 => Self::AlterCommand,
            108 => Self::LBRACE_AlterCommandsList_OptSemicolons_RBRACE,
            109 => Self::LBRACE_OptSemicolons_RBRACE,
            110 => Self::LBRACE_Semicolons_AlterCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            111 => Self::AlterCommand,
            112 => Self::AlterCommandsList_Semicolons_AlterCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterConcreteConstraintCommand {
    fn from_id(id: usize) -> Self {
        match id {
            113 => Self::AlterAbstract,
            114 => Self::AlterAnnotationValueStmt,
            115 => Self::AlterOwnedStmt,
            116 => Self::CreateAnnotationValueStmt,
            117 => Self::DropAnnotationValueStmt,
            118 => Self::ResetFieldStmt,
            119 => Self::SetDelegatedStmt,
            120 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterConcreteConstraintCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            121 => Self::AlterConcreteConstraintCommand,
            122 => Self::LBRACE_AlterConcreteConstraintCommandsList_OptSemicolons_RBRACE,
            123 => Self::LBRACE_OptSemicolons_RBRACE,
            124 => Self::LBRACE_Semicolons_AlterConcreteConstraintCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterConcreteConstraintCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            125 => Self::AlterConcreteConstraintCommand,
            126 => Self::AlterConcreteConstraintCommandsList_Semicolons_AlterConcreteConstraintCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterConcreteConstraintStmt {
    fn from_id(id: usize) -> Self {
        match id {
            127 => Self::ALTER_CONSTRAINT_NodeName_OptConcreteConstraintArgList_OptOnExpr_OptExceptExpr_AlterConcreteConstraintCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterConcreteIndexCommand {
    fn from_id(id: usize) -> Self {
        match id {
            128 => Self::AlterAnnotationValueStmt,
            129 => Self::AlterDeferredStmt,
            130 => Self::AlterOwnedStmt,
            131 => Self::CreateAnnotationValueStmt,
            132 => Self::DropAnnotationValueStmt,
            133 => Self::ResetFieldStmt,
            134 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterConcreteIndexCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            135 => Self::AlterConcreteIndexCommand,
            136 => Self::LBRACE_AlterConcreteIndexCommandsList_OptSemicolons_RBRACE,
            137 => Self::LBRACE_OptSemicolons_RBRACE,
            138 => Self::LBRACE_Semicolons_AlterConcreteIndexCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterConcreteIndexCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            139 => Self::AlterConcreteIndexCommand,
            140 => Self::AlterConcreteIndexCommandsList_Semicolons_AlterConcreteIndexCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterConcreteIndexStmt {
    fn from_id(id: usize) -> Self {
        match id {
            141 => Self::ALTER_INDEX_OnExpr_OptExceptExpr_AlterConcreteIndexCommandsBlock,
            142 => Self::ALTER_INDEX_NodeName_OptIndexExtArgList_OnExpr_OptExceptExpr_AlterConcreteIndexCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterConcreteLinkCommand {
    fn from_id(id: usize) -> Self {
        match id {
            143 => Self::AlterAnnotationValueStmt,
            144 => Self::AlterConcreteConstraintStmt,
            145 => Self::AlterConcreteIndexStmt,
            146 => Self::AlterConcretePropertyStmt,
            147 => Self::AlterOwnedStmt,
            148 => Self::AlterRewriteStmt,
            149 => Self::AlterSimpleExtending,
            150 => Self::CreateAnnotationValueStmt,
            151 => Self::CreateConcreteConstraintStmt,
            152 => Self::CreateConcreteIndexStmt,
            153 => Self::CreateConcretePropertyStmt,
            154 => Self::CreateRewriteStmt,
            155 => Self::DropAnnotationValueStmt,
            156 => Self::DropConcreteConstraintStmt,
            157 => Self::DropConcreteIndexStmt,
            158 => Self::DropConcretePropertyStmt,
            159 => Self::DropRewriteStmt,
            160 => Self::OnSourceDeleteResetStmt,
            161 => Self::OnSourceDeleteStmt,
            162 => Self::OnTargetDeleteResetStmt,
            163 => Self::OnTargetDeleteStmt,
            164 => Self::RenameStmt,
            165 => Self::ResetFieldStmt,
            166 => Self::SetCardinalityStmt,
            167 => Self::SetFieldStmt,
            168 => Self::SetPointerTypeStmt,
            169 => Self::SetRequiredStmt,
            170 => Self::UsingStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterConcreteLinkCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            171 => Self::AlterConcreteLinkCommand,
            172 => Self::LBRACE_AlterConcreteLinkCommandsList_OptSemicolons_RBRACE,
            173 => Self::LBRACE_OptSemicolons_RBRACE,
            174 => Self::LBRACE_Semicolons_AlterConcreteLinkCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterConcreteLinkCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            175 => Self::AlterConcreteLinkCommand,
            176 => Self::AlterConcreteLinkCommandsList_Semicolons_AlterConcreteLinkCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterConcreteLinkStmt {
    fn from_id(id: usize) -> Self {
        match id {
            177 => Self::ALTER_LINK_UnqualifiedPointerName_AlterConcreteLinkCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterConcretePropertyCommand {
    fn from_id(id: usize) -> Self {
        match id {
            178 => Self::AlterAnnotationValueStmt,
            179 => Self::AlterConcreteConstraintStmt,
            180 => Self::AlterOwnedStmt,
            181 => Self::AlterRewriteStmt,
            182 => Self::AlterSimpleExtending,
            183 => Self::CreateAnnotationValueStmt,
            184 => Self::CreateConcreteConstraintStmt,
            185 => Self::CreateRewriteStmt,
            186 => Self::DropAnnotationValueStmt,
            187 => Self::DropConcreteConstraintStmt,
            188 => Self::DropRewriteStmt,
            189 => Self::RenameStmt,
            190 => Self::ResetFieldStmt,
            191 => Self::SetCardinalityStmt,
            192 => Self::SetFieldStmt,
            193 => Self::SetPointerTypeStmt,
            194 => Self::SetRequiredStmt,
            195 => Self::UsingStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterConcretePropertyCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            196 => Self::AlterConcretePropertyCommand,
            197 => Self::LBRACE_AlterConcretePropertyCommandsList_OptSemicolons_RBRACE,
            198 => Self::LBRACE_OptSemicolons_RBRACE,
            199 => Self::LBRACE_Semicolons_AlterConcretePropertyCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterConcretePropertyCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            200 => Self::AlterConcretePropertyCommand,
            201 => Self::AlterConcretePropertyCommandsList_Semicolons_AlterConcretePropertyCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterConcretePropertyStmt {
    fn from_id(id: usize) -> Self {
        match id {
            202 => Self::ALTER_PROPERTY_UnqualifiedPointerName_AlterConcretePropertyCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterConstraintStmt {
    fn from_id(id: usize) -> Self {
        match id {
            203 => Self::ALTER_ABSTRACT_CONSTRAINT_NodeName_AlterCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterCurrentMigrationStmt {
    fn from_id(id: usize) -> Self {
        match id {
            204 => Self::ALTER_CURRENT_MIGRATION_REJECT_PROPOSED,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterDatabaseCommand {
    fn from_id(id: usize) -> Self {
        match id {
            205 => Self::RenameStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterDatabaseCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            206 => Self::AlterDatabaseCommand,
            207 => Self::LBRACE_AlterDatabaseCommandsList_OptSemicolons_RBRACE,
            208 => Self::LBRACE_OptSemicolons_RBRACE,
            209 => Self::LBRACE_Semicolons_AlterDatabaseCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterDatabaseCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            210 => Self::AlterDatabaseCommand,
            211 => Self::AlterDatabaseCommandsList_Semicolons_AlterDatabaseCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterDatabaseStmt {
    fn from_id(id: usize) -> Self {
        match id {
            212 => Self::ALTER_DATABASE_DatabaseName_AlterDatabaseCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterDeferredStmt {
    fn from_id(id: usize) -> Self {
        match id {
            213 => Self::DROP_DEFERRED,
            214 => Self::SET_DEFERRED,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterExtending {
    fn from_id(id: usize) -> Self {
        match id {
            215 => Self::AlterAbstract,
            216 => Self::DROP_EXTENDING_TypeNameList,
            217 => Self::EXTENDING_TypeNameList_OptPosition,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterExtensionStmt {
    fn from_id(id: usize) -> Self {
        match id {
            218 => Self::ALTER_EXTENSION_ShortNodeName_TO_ExtensionVersion,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterFunctionCommand {
    fn from_id(id: usize) -> Self {
        match id {
            219 => Self::AlterAnnotationValueStmt,
            220 => Self::CreateAnnotationValueStmt,
            221 => Self::DropAnnotationValueStmt,
            222 => Self::FromFunction,
            223 => Self::RenameStmt,
            224 => Self::ResetFieldStmt,
            225 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterFunctionCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            226 => Self::AlterFunctionCommand,
            227 => Self::LBRACE_AlterFunctionCommandsList_OptSemicolons_RBRACE,
            228 => Self::LBRACE_OptSemicolons_RBRACE,
            229 => Self::LBRACE_Semicolons_AlterFunctionCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterFunctionCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            230 => Self::AlterFunctionCommand,
            231 => Self::AlterFunctionCommandsList_Semicolons_AlterFunctionCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterFunctionStmt {
    fn from_id(id: usize) -> Self {
        match id {
            232 => Self::ALTER_FUNCTION_NodeName_CreateFunctionArgs_AlterFunctionCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterGlobalCommand {
    fn from_id(id: usize) -> Self {
        match id {
            233 => Self::AlterAnnotationValueStmt,
            234 => Self::CreateAnnotationValueStmt,
            235 => Self::DropAnnotationValueStmt,
            236 => Self::RenameStmt,
            237 => Self::ResetFieldStmt,
            238 => Self::SetCardinalityStmt,
            239 => Self::SetFieldStmt,
            240 => Self::SetGlobalTypeStmt,
            241 => Self::SetRequiredStmt,
            242 => Self::UsingStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterGlobalCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            243 => Self::AlterGlobalCommand,
            244 => Self::LBRACE_AlterGlobalCommandsList_OptSemicolons_RBRACE,
            245 => Self::LBRACE_OptSemicolons_RBRACE,
            246 => Self::LBRACE_Semicolons_AlterGlobalCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterGlobalCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            247 => Self::AlterGlobalCommand,
            248 => Self::AlterGlobalCommandsList_Semicolons_AlterGlobalCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterGlobalStmt {
    fn from_id(id: usize) -> Self {
        match id {
            249 => Self::ALTER_GLOBAL_NodeName_AlterGlobalCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterIndexCommand {
    fn from_id(id: usize) -> Self {
        match id {
            250 => Self::AlterAnnotationValueStmt,
            251 => Self::CreateAnnotationValueStmt,
            252 => Self::DropAnnotationValueStmt,
            253 => Self::RenameStmt,
            254 => Self::ResetFieldStmt,
            255 => Self::SetFieldStmt,
            256 => Self::UsingStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterIndexCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            257 => Self::AlterIndexCommand,
            258 => Self::LBRACE_AlterIndexCommandsList_OptSemicolons_RBRACE,
            259 => Self::LBRACE_OptSemicolons_RBRACE,
            260 => Self::LBRACE_Semicolons_AlterIndexCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterIndexCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            261 => Self::AlterIndexCommand,
            262 => Self::AlterIndexCommandsList_Semicolons_AlterIndexCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterIndexStmt {
    fn from_id(id: usize) -> Self {
        match id {
            263 => Self::ALTER_ABSTRACT_INDEX_NodeName_AlterIndexCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterLinkCommand {
    fn from_id(id: usize) -> Self {
        match id {
            264 => Self::AlterAnnotationValueStmt,
            265 => Self::AlterConcreteConstraintStmt,
            266 => Self::AlterConcreteIndexStmt,
            267 => Self::AlterConcretePropertyStmt,
            268 => Self::AlterRewriteStmt,
            269 => Self::AlterSimpleExtending,
            270 => Self::CreateAnnotationValueStmt,
            271 => Self::CreateConcreteConstraintStmt,
            272 => Self::CreateConcreteIndexStmt,
            273 => Self::CreateConcretePropertyStmt,
            274 => Self::CreateRewriteStmt,
            275 => Self::DropAnnotationValueStmt,
            276 => Self::DropConcreteConstraintStmt,
            277 => Self::DropConcreteIndexStmt,
            278 => Self::DropConcretePropertyStmt,
            279 => Self::DropRewriteStmt,
            280 => Self::RenameStmt,
            281 => Self::ResetFieldStmt,
            282 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterLinkCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            283 => Self::AlterLinkCommand,
            284 => Self::LBRACE_AlterLinkCommandsList_OptSemicolons_RBRACE,
            285 => Self::LBRACE_OptSemicolons_RBRACE,
            286 => Self::LBRACE_Semicolons_AlterLinkCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterLinkCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            287 => Self::AlterLinkCommand,
            288 => Self::AlterLinkCommandsList_Semicolons_AlterLinkCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterLinkStmt {
    fn from_id(id: usize) -> Self {
        match id {
            289 => Self::ALTER_ABSTRACT_LINK_PtrNodeName_AlterLinkCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterMigrationCommand {
    fn from_id(id: usize) -> Self {
        match id {
            290 => Self::ResetFieldStmt,
            291 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterMigrationCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            292 => Self::AlterMigrationCommand,
            293 => Self::LBRACE_AlterMigrationCommandsList_OptSemicolons_RBRACE,
            294 => Self::LBRACE_OptSemicolons_RBRACE,
            295 => Self::LBRACE_Semicolons_AlterMigrationCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterMigrationCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            296 => Self::AlterMigrationCommand,
            297 => Self::AlterMigrationCommandsList_Semicolons_AlterMigrationCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterMigrationStmt {
    fn from_id(id: usize) -> Self {
        match id {
            298 => Self::ALTER_MIGRATION_NodeName_AlterMigrationCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterModuleStmt {
    fn from_id(id: usize) -> Self {
        match id {
            299 => Self::ALTER_MODULE_ModuleName_AlterCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterObjectTypeCommand {
    fn from_id(id: usize) -> Self {
        match id {
            300 => Self::AlterAccessPolicyStmt,
            301 => Self::AlterAnnotationValueStmt,
            302 => Self::AlterConcreteConstraintStmt,
            303 => Self::AlterConcreteIndexStmt,
            304 => Self::AlterConcreteLinkStmt,
            305 => Self::AlterConcretePropertyStmt,
            306 => Self::AlterSimpleExtending,
            307 => Self::AlterTriggerStmt,
            308 => Self::CreateAccessPolicyStmt,
            309 => Self::CreateAnnotationValueStmt,
            310 => Self::CreateConcreteConstraintStmt,
            311 => Self::CreateConcreteIndexStmt,
            312 => Self::CreateConcreteLinkStmt,
            313 => Self::CreateConcretePropertyStmt,
            314 => Self::CreateTriggerStmt,
            315 => Self::DropAccessPolicyStmt,
            316 => Self::DropAnnotationValueStmt,
            317 => Self::DropConcreteConstraintStmt,
            318 => Self::DropConcreteIndexStmt,
            319 => Self::DropConcreteLinkStmt,
            320 => Self::DropConcretePropertyStmt,
            321 => Self::DropTriggerStmt,
            322 => Self::RenameStmt,
            323 => Self::ResetFieldStmt,
            324 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterObjectTypeCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            325 => Self::AlterObjectTypeCommand,
            326 => Self::LBRACE_AlterObjectTypeCommandsList_OptSemicolons_RBRACE,
            327 => Self::LBRACE_OptSemicolons_RBRACE,
            328 => Self::LBRACE_Semicolons_AlterObjectTypeCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterObjectTypeCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            329 => Self::AlterObjectTypeCommand,
            330 => Self::AlterObjectTypeCommandsList_Semicolons_AlterObjectTypeCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterObjectTypeStmt {
    fn from_id(id: usize) -> Self {
        match id {
            331 => Self::ALTER_TYPE_NodeName_AlterObjectTypeCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterOperatorCommand {
    fn from_id(id: usize) -> Self {
        match id {
            332 => Self::AlterAnnotationValueStmt,
            333 => Self::CreateAnnotationValueStmt,
            334 => Self::DropAnnotationValueStmt,
            335 => Self::ResetFieldStmt,
            336 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterOperatorCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            337 => Self::AlterOperatorCommand,
            338 => Self::LBRACE_AlterOperatorCommandsList_OptSemicolons_RBRACE,
            339 => Self::LBRACE_OptSemicolons_RBRACE,
            340 => Self::LBRACE_Semicolons_AlterOperatorCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterOperatorCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            341 => Self::AlterOperatorCommand,
            342 => Self::AlterOperatorCommandsList_Semicolons_AlterOperatorCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterOperatorStmt {
    fn from_id(id: usize) -> Self {
        match id {
            343 => Self::ALTER_OperatorKind_OPERATOR_NodeName_CreateFunctionArgs_AlterOperatorCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterOwnedStmt {
    fn from_id(id: usize) -> Self {
        match id {
            344 => Self::DROP_OWNED,
            345 => Self::SET_OWNED,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterPermissionCommand {
    fn from_id(id: usize) -> Self {
        match id {
            346 => Self::AlterAnnotationValueStmt,
            347 => Self::CreateAnnotationValueStmt,
            348 => Self::DropAnnotationValueStmt,
            349 => Self::RenameStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterPermissionCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            350 => Self::AlterPermissionCommand,
            351 => Self::LBRACE_AlterPermissionCommandsList_OptSemicolons_RBRACE,
            352 => Self::LBRACE_OptSemicolons_RBRACE,
            353 => Self::LBRACE_Semicolons_AlterPermissionCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterPermissionCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            354 => Self::AlterPermissionCommand,
            355 => Self::AlterPermissionCommandsList_Semicolons_AlterPermissionCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterPermissionStmt {
    fn from_id(id: usize) -> Self {
        match id {
            356 => Self::ALTER_PERMISSION_NodeName_AlterPermissionCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterPropertyCommand {
    fn from_id(id: usize) -> Self {
        match id {
            357 => Self::AlterAnnotationValueStmt,
            358 => Self::AlterRewriteStmt,
            359 => Self::CreateAnnotationValueStmt,
            360 => Self::CreateRewriteStmt,
            361 => Self::DropAnnotationValueStmt,
            362 => Self::DropRewriteStmt,
            363 => Self::RenameStmt,
            364 => Self::ResetFieldStmt,
            365 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterPropertyCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            366 => Self::AlterPropertyCommand,
            367 => Self::LBRACE_AlterPropertyCommandsList_OptSemicolons_RBRACE,
            368 => Self::LBRACE_OptSemicolons_RBRACE,
            369 => Self::LBRACE_Semicolons_AlterPropertyCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterPropertyCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            370 => Self::AlterPropertyCommand,
            371 => Self::AlterPropertyCommandsList_Semicolons_AlterPropertyCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterPropertyStmt {
    fn from_id(id: usize) -> Self {
        match id {
            372 => Self::ALTER_ABSTRACT_PROPERTY_PtrNodeName_AlterPropertyCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterRewriteCommand {
    fn from_id(id: usize) -> Self {
        match id {
            373 => Self::AlterAnnotationValueStmt,
            374 => Self::CreateAnnotationValueStmt,
            375 => Self::DropAnnotationValueStmt,
            376 => Self::ResetFieldStmt,
            377 => Self::SetFieldStmt,
            378 => Self::UsingStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterRewriteCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            379 => Self::AlterRewriteCommand,
            380 => Self::LBRACE_AlterRewriteCommandsList_OptSemicolons_RBRACE,
            381 => Self::LBRACE_OptSemicolons_RBRACE,
            382 => Self::LBRACE_Semicolons_AlterRewriteCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterRewriteCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            383 => Self::AlterRewriteCommand,
            384 => Self::AlterRewriteCommandsList_Semicolons_AlterRewriteCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterRewriteStmt {
    fn from_id(id: usize) -> Self {
        match id {
            385 => Self::ALTER_REWRITE_RewriteKindList_AlterRewriteCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterRoleCommand {
    fn from_id(id: usize) -> Self {
        match id {
            386 => Self::AlterRoleExtending,
            387 => Self::RenameStmt,
            388 => Self::ResetFieldStmt,
            389 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterRoleCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            390 => Self::AlterRoleCommand,
            391 => Self::LBRACE_AlterRoleCommandsList_OptSemicolons_RBRACE,
            392 => Self::LBRACE_OptSemicolons_RBRACE,
            393 => Self::LBRACE_Semicolons_AlterRoleCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterRoleCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            394 => Self::AlterRoleCommand,
            395 => Self::AlterRoleCommandsList_Semicolons_AlterRoleCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterRoleExtending {
    fn from_id(id: usize) -> Self {
        match id {
            396 => Self::DROP_EXTENDING_ShortTypeNameList,
            397 => Self::EXTENDING_ShortTypeNameList_OptPosition,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterRoleStmt {
    fn from_id(id: usize) -> Self {
        match id {
            398 => Self::ALTER_ROLE_ShortNodeName_AlterRoleCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterScalarTypeCommand {
    fn from_id(id: usize) -> Self {
        match id {
            399 => Self::AlterAnnotationValueStmt,
            400 => Self::AlterConcreteConstraintStmt,
            401 => Self::AlterExtending,
            402 => Self::CreateAnnotationValueStmt,
            403 => Self::CreateConcreteConstraintStmt,
            404 => Self::DropAnnotationValueStmt,
            405 => Self::DropConcreteConstraintStmt,
            406 => Self::RenameStmt,
            407 => Self::ResetFieldStmt,
            408 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterScalarTypeCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            409 => Self::AlterScalarTypeCommand,
            410 => Self::LBRACE_AlterScalarTypeCommandsList_OptSemicolons_RBRACE,
            411 => Self::LBRACE_OptSemicolons_RBRACE,
            412 => Self::LBRACE_Semicolons_AlterScalarTypeCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterScalarTypeCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            413 => Self::AlterScalarTypeCommand,
            414 => Self::AlterScalarTypeCommandsList_Semicolons_AlterScalarTypeCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterScalarTypeStmt {
    fn from_id(id: usize) -> Self {
        match id {
            415 => Self::ALTER_SCALAR_TYPE_NodeName_AlterScalarTypeCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterSimpleExtending {
    fn from_id(id: usize) -> Self {
        match id {
            416 => Self::AlterAbstract,
            417 => Self::DROP_EXTENDING_SimpleTypeNameList,
            418 => Self::EXTENDING_SimpleTypeNameList_OptPosition,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterTriggerCommand {
    fn from_id(id: usize) -> Self {
        match id {
            419 => Self::AccessWhenStmt,
            420 => Self::AlterAnnotationValueStmt,
            421 => Self::CreateAnnotationValueStmt,
            422 => Self::DropAnnotationValueStmt,
            423 => Self::RenameStmt,
            424 => Self::ResetFieldStmt,
            425 => Self::SetFieldStmt,
            426 => Self::UsingStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterTriggerCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            427 => Self::AlterTriggerCommand,
            428 => Self::LBRACE_AlterTriggerCommandsList_OptSemicolons_RBRACE,
            429 => Self::LBRACE_OptSemicolons_RBRACE,
            430 => Self::LBRACE_Semicolons_AlterTriggerCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterTriggerCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            431 => Self::AlterTriggerCommand,
            432 => Self::AlterTriggerCommandsList_Semicolons_AlterTriggerCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AlterTriggerStmt {
    fn from_id(id: usize) -> Self {
        match id {
            433 => Self::ALTER_TRIGGER_UnqualifiedPointerName_AlterTriggerCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AnalyzeStmt {
    fn from_id(id: usize) -> Self {
        match id {
            434 => Self::ANALYZE_ExprStmt,
            435 => Self::ANALYZE_NamedTuple_ExprStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AnnotationDeclaration {
    fn from_id(id: usize) -> Self {
        match id {
            436 => Self::ABSTRACT_ANNOTATION_NodeName_OptExtendingSimple_CreateSDLCommandsBlock,
            437 => Self::ABSTRACT_INHERITABLE_ANNOTATION_NodeName_OptExtendingSimple_CreateSDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AnnotationDeclarationShort {
    fn from_id(id: usize) -> Self {
        match id {
            438 => Self::ABSTRACT_ANNOTATION_NodeName_OptExtendingSimple,
            439 => Self::ABSTRACT_INHERITABLE_ANNOTATION_NodeName_OptExtendingSimple,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AnnoyingFor {
    fn from_id(id: usize) -> Self {
        match id {
            440 => Self::FOR_OptionalOptional_Identifier_IN_AtomicExpr_ExprStmtAnnoying,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AnyIdentifier {
    fn from_id(id: usize) -> Self {
        match id {
            441 => Self::PtrIdentifier,
            442 => Self::ReservedKeyword,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AnyNodeName {
    fn from_id(id: usize) -> Self {
        match id {
            443 => Self::AnyIdentifier,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AtomicExpr {
    fn from_id(id: usize) -> Self {
        match id {
            444 => Self::AtomicPath,
            445 => Self::BaseAtomicExpr,
            446 => Self::LANGBRACKET_FullTypeExpr_RANGBRACKET_AtomicExpr_P_TYPECAST,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::AtomicPath {
    fn from_id(id: usize) -> Self {
        match id {
            447 => Self::AtomicExpr_PathStep_P_DOT,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::BaseAtomicExpr {
    fn from_id(id: usize) -> Self {
        match id {
            448 => Self::Collection,
            449 => Self::Constant,
            450 => Self::DUNDERDEFAULT,
            451 => Self::DUNDERNEW,
            452 => Self::DUNDEROLD,
            453 => Self::DUNDERSOURCE,
            454 => Self::DUNDERSPECIFIED,
            455 => Self::DUNDERSUBJECT,
            456 => Self::FreeShape,
            457 => Self::FuncExpr,
            458 => Self::NamedTuple,
            459 => Self::NodeName_P_DOT,
            460 => Self::ParenExpr_P_UMINUS,
            461 => Self::PathStep_P_DOT,
            462 => Self::Set,
            463 => Self::StringInterpolation,
            464 => Self::Tuple,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::BaseBooleanConstant {
    fn from_id(id: usize) -> Self {
        match id {
            465 => Self::FALSE,
            466 => Self::TRUE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::BaseBytesConstant {
    fn from_id(id: usize) -> Self {
        match id {
            467 => Self::BCONST,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::BaseName {
    fn from_id(id: usize) -> Self {
        match id {
            468 => Self::Identifier,
            469 => Self::QualifiedName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::BaseNumberConstant {
    fn from_id(id: usize) -> Self {
        match id {
            470 => Self::FCONST,
            471 => Self::ICONST,
            472 => Self::NFCONST,
            473 => Self::NICONST,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::BaseStringConstant {
    fn from_id(id: usize) -> Self {
        match id {
            474 => Self::SCONST,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::BranchOptions {
    fn from_id(id: usize) -> Self {
        match id {
            475 => Self::FORCE,
            476 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::BranchStmt {
    fn from_id(id: usize) -> Self {
        match id {
            477 => Self::AlterBranchStmt,
            478 => Self::CreateBranchStmt,
            479 => Self::DropBranchStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ByClause {
    fn from_id(id: usize) -> Self {
        match id {
            480 => Self::BY_GroupingElementList,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CastAllowedUse {
    fn from_id(id: usize) -> Self {
        match id {
            481 => Self::ALLOW_ASSIGNMENT,
            482 => Self::ALLOW_IMPLICIT,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CastCode {
    fn from_id(id: usize) -> Self {
        match id {
            483 => Self::USING_Identifier_BaseStringConstant,
            484 => Self::USING_Identifier_CAST,
            485 => Self::USING_Identifier_EXPRESSION,
            486 => Self::USING_Identifier_FUNCTION_BaseStringConstant,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::Collection {
    fn from_id(id: usize) -> Self {
        match id {
            487 => Self::LBRACKET_OptExprList_RBRACKET,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CollectionTypeName {
    fn from_id(id: usize) -> Self {
        match id {
            488 => Self::NodeName_LANGBRACKET_RANGBRACKET,
            489 => Self::NodeName_LANGBRACKET_SubtypeList_RANGBRACKET,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ColonedIdents {
    fn from_id(id: usize) -> Self {
        match id {
            490 => Self::AnyIdentifier,
            491 => Self::ColonedIdents_DOUBLECOLON_AnyIdentifier,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CommitMigrationStmt {
    fn from_id(id: usize) -> Self {
        match id {
            492 => Self::COMMIT_MIGRATION,
            493 => Self::COMMIT_MIGRATION_REWRITE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CompareOp {
    fn from_id(id: usize) -> Self {
        match id {
            494 => Self::DISTINCTFROM_P_COMPARE_OP,
            495 => Self::EQUALS_P_COMPARE_OP,
            496 => Self::GREATEREQ_P_COMPARE_OP,
            497 => Self::LANGBRACKET_P_COMPARE_OP,
            498 => Self::LESSEQ_P_COMPARE_OP,
            499 => Self::NOTDISTINCTFROM_P_COMPARE_OP,
            500 => Self::NOTEQ_P_COMPARE_OP,
            501 => Self::RANGBRACKET_P_COMPARE_OP,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ComputableShapePointer {
    fn from_id(id: usize) -> Self {
        match id {
            502 => Self::MULTI_SimpleShapePointer_ASSIGN_GenExpr,
            503 => Self::OPTIONAL_MULTI_SimpleShapePointer_ASSIGN_GenExpr,
            504 => Self::OPTIONAL_SINGLE_SimpleShapePointer_ASSIGN_GenExpr,
            505 => Self::OPTIONAL_SimpleShapePointer_ASSIGN_GenExpr,
            506 => Self::REQUIRED_MULTI_SimpleShapePointer_ASSIGN_GenExpr,
            507 => Self::REQUIRED_SINGLE_SimpleShapePointer_ASSIGN_GenExpr,
            508 => Self::REQUIRED_SimpleShapePointer_ASSIGN_GenExpr,
            509 => Self::SINGLE_SimpleShapePointer_ASSIGN_GenExpr,
            510 => Self::SimpleShapePointer_ADDASSIGN_GenExpr,
            511 => Self::SimpleShapePointer_ASSIGN_GenExpr,
            512 => Self::SimpleShapePointer_REMASSIGN_GenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ConcreteConstraintBlock {
    fn from_id(id: usize) -> Self {
        match id {
            513 => Self::CONSTRAINT_NodeName_OptConcreteConstraintArgList_OptOnExpr_OptExceptExpr_CreateSDLCommandsBlock,
            514 => Self::DELEGATED_CONSTRAINT_NodeName_OptConcreteConstraintArgList_OptOnExpr_OptExceptExpr_CreateSDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ConcreteConstraintShort {
    fn from_id(id: usize) -> Self {
        match id {
            515 => Self::CONSTRAINT_NodeName_OptConcreteConstraintArgList_OptOnExpr_OptExceptExpr,
            516 => Self::DELEGATED_CONSTRAINT_NodeName_OptConcreteConstraintArgList_OptOnExpr_OptExceptExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ConcreteIndexDeclarationBlock {
    fn from_id(id: usize) -> Self {
        match id {
            517 => Self::DEFERRED_INDEX_OnExpr_OptExceptExpr_CreateConcreteIndexSDLCommandsBlock,
            518 => Self::INDEX_OnExpr_OptExceptExpr_CreateConcreteIndexSDLCommandsBlock,
            519 => Self::DEFERRED_INDEX_NodeName_OnExpr_OptExceptExpr_CreateConcreteIndexSDLCommandsBlock,
            520 => Self::DEFERRED_INDEX_NodeName_IndexExtArgList_OnExpr_OptExceptExpr_CreateConcreteIndexSDLCommandsBlock,
            521 => Self::INDEX_NodeName_OnExpr_OptExceptExpr_CreateConcreteIndexSDLCommandsBlock,
            522 => Self::INDEX_NodeName_IndexExtArgList_OnExpr_OptExceptExpr_CreateConcreteIndexSDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ConcreteIndexDeclarationShort {
    fn from_id(id: usize) -> Self {
        match id {
            523 => Self::DEFERRED_INDEX_NodeName_OnExpr_OptExceptExpr,
            524 => Self::DEFERRED_INDEX_NodeName_IndexExtArgList_OnExpr_OptExceptExpr,
            525 => Self::INDEX_NodeName_OnExpr_OptExceptExpr,
            526 => Self::INDEX_NodeName_IndexExtArgList_OnExpr_OptExceptExpr,
            527 => Self::DEFERRED_INDEX_OnExpr_OptExceptExpr,
            528 => Self::INDEX_OnExpr_OptExceptExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ConcreteLinkBlock {
    fn from_id(id: usize) -> Self {
        match id {
            529 => Self::OVERLOADED_LINK_PathNodeName_OptExtendingSimple_OptPtrTarget_CreateConcreteLinkSDLCommandsBlock,
            530 => Self::OVERLOADED_PtrQuals_LINK_PathNodeName_OptExtendingSimple_OptPtrTarget_CreateConcreteLinkSDLCommandsBlock,
            531 => Self::LINK_PathNodeName_OptExtendingSimple_OptPtrTarget_CreateConcreteLinkSDLCommandsBlock,
            532 => Self::PtrQuals_LINK_PathNodeName_OptExtendingSimple_OptPtrTarget_CreateConcreteLinkSDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ConcreteLinkShort {
    fn from_id(id: usize) -> Self {
        match id {
            533 => Self::LINK_PathNodeName_ASSIGN_GenExpr,
            534 => Self::OVERLOADED_LINK_PathNodeName_OptExtendingSimple_OptPtrTarget,
            535 => Self::OVERLOADED_PtrQuals_LINK_PathNodeName_OptExtendingSimple_OptPtrTarget,
            536 => Self::PtrQuals_LINK_PathNodeName_ASSIGN_GenExpr,
            537 => Self::LINK_PathNodeName_OptExtendingSimple_PtrTarget,
            538 => Self::PtrQuals_LINK_PathNodeName_OptExtendingSimple_PtrTarget,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ConcretePropertyBlock {
    fn from_id(id: usize) -> Self {
        match id {
            539 => Self::OVERLOADED_PROPERTY_PathNodeName_OptExtendingSimple_OptPtrTarget_CreateConcretePropertySDLCommandsBlock,
            540 => Self::OVERLOADED_PtrQuals_PROPERTY_PathNodeName_OptExtendingSimple_OptPtrTarget_CreateConcretePropertySDLCommandsBlock,
            541 => Self::PROPERTY_PathNodeName_OptExtendingSimple_OptPtrTarget_CreateConcretePropertySDLCommandsBlock,
            542 => Self::PtrQuals_PROPERTY_PathNodeName_OptExtendingSimple_OptPtrTarget_CreateConcretePropertySDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ConcretePropertyShort {
    fn from_id(id: usize) -> Self {
        match id {
            543 => Self::PROPERTY_PathNodeName_ASSIGN_GenExpr,
            544 => Self::OVERLOADED_PROPERTY_PathNodeName_OptExtendingSimple_OptPtrTarget,
            545 => Self::OVERLOADED_PtrQuals_PROPERTY_PathNodeName_OptExtendingSimple_OptPtrTarget,
            546 => Self::PtrQuals_PROPERTY_PathNodeName_ASSIGN_GenExpr,
            547 => Self::PROPERTY_PathNodeName_OptExtendingSimple_PtrTarget,
            548 => Self::PtrQuals_PROPERTY_PathNodeName_OptExtendingSimple_PtrTarget,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ConcreteUnknownPointerBlock {
    fn from_id(id: usize) -> Self {
        match id {
            549 => Self::OVERLOADED_PathNodeName_OptExtendingSimple_OptPtrTarget_CreateConcreteLinkSDLCommandsBlock,
            550 => Self::OVERLOADED_PtrQuals_PathNodeName_OptExtendingSimple_OptPtrTarget_CreateConcreteLinkSDLCommandsBlock,
            551 => Self::PathNodeName_OptExtendingSimple_OptPtrTarget_CreateConcreteLinkSDLCommandsBlock,
            552 => Self::PtrQuals_PathNodeName_OptExtendingSimple_OptPtrTarget_CreateConcreteLinkSDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ConcreteUnknownPointerObjectShort {
    fn from_id(id: usize) -> Self {
        match id {
            553 => Self::PathNodeName_ASSIGN_GenExpr,
            554 => Self::PtrQuals_PathNodeName_ASSIGN_GenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ConcreteUnknownPointerShort {
    fn from_id(id: usize) -> Self {
        match id {
            555 => Self::OVERLOADED_PathNodeName_OptExtendingSimple_OptPtrTarget,
            556 => Self::OVERLOADED_PtrQuals_PathNodeName_OptExtendingSimple_OptPtrTarget,
            557 => Self::PathNodeName_OptExtendingSimple_PtrTarget,
            558 => Self::PtrQuals_PathNodeName_OptExtendingSimple_PtrTarget,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ConfigOp {
    fn from_id(id: usize) -> Self {
        match id {
            559 => Self::INSERT_NodeName_Shape,
            560 => Self::RESET_NodeName_OptFilterClause,
            561 => Self::SET_NodeName_ASSIGN_Expr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ConfigScope {
    fn from_id(id: usize) -> Self {
        match id {
            562 => Self::CURRENT_BRANCH,
            563 => Self::CURRENT_DATABASE,
            564 => Self::INSTANCE,
            565 => Self::SESSION,
            566 => Self::SYSTEM,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ConfigStmt {
    fn from_id(id: usize) -> Self {
        match id {
            567 => Self::CONFIGURE_BRANCH_ConfigOp,
            568 => Self::CONFIGURE_ConfigScope_ConfigOp,
            569 => Self::CONFIGURE_DATABASE_ConfigOp,
            570 => Self::RESET_GLOBAL_NodeName,
            571 => Self::SET_GLOBAL_NodeName_ASSIGN_Expr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::Constant {
    fn from_id(id: usize) -> Self {
        match id {
            572 => Self::BaseBooleanConstant,
            573 => Self::BaseBytesConstant,
            574 => Self::BaseNumberConstant,
            575 => Self::BaseStringConstant,
            576 => Self::PARAMETER,
            577 => Self::PARAMETERANDTYPE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ConstraintDeclaration {
    fn from_id(id: usize) -> Self {
        match id {
            578 => Self::ABSTRACT_CONSTRAINT_NodeName_OptOnExpr_OptExtendingSimple_CreateSDLCommandsBlock,
            579 => Self::ABSTRACT_CONSTRAINT_NodeName_CreateFunctionArgs_OptOnExpr_OptExtendingSimple_CreateSDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ConstraintDeclarationShort {
    fn from_id(id: usize) -> Self {
        match id {
            580 => Self::ABSTRACT_CONSTRAINT_NodeName_OptOnExpr_OptExtendingSimple,
            581 => Self::ABSTRACT_CONSTRAINT_NodeName_CreateFunctionArgs_OptOnExpr_OptExtendingSimple,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAccessPolicyCommand {
    fn from_id(id: usize) -> Self {
        match id {
            582 => Self::CreateAnnotationValueStmt,
            583 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAccessPolicyCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            584 => Self::LBRACE_CreateAccessPolicyCommandsList_OptSemicolons_RBRACE,
            585 => Self::LBRACE_OptSemicolons_RBRACE,
            586 => Self::LBRACE_Semicolons_CreateAccessPolicyCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAccessPolicyCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            587 => Self::CreateAccessPolicyCommand,
            588 => Self::CreateAccessPolicyCommandsList_Semicolons_CreateAccessPolicyCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAccessPolicySDLCommandFull {
    fn from_id(id: usize) -> Self {
        match id {
            590 => Self::CreateAccessPolicySDLCommandShort_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAccessPolicySDLCommandShort {
    fn from_id(id: usize) -> Self {
        match id {
            591 => Self::SetAnnotation,
            592 => Self::SetField,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAccessPolicySDLCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            593 => Self::LBRACE_OptSemicolons_CreateAccessPolicySDLCommandShort_RBRACE,
            594 => Self::LBRACE_OptSemicolons_CreateAccessPolicySDLCommandsList_OptSemicolons_CreateAccessPolicySDLCommandShort_RBRACE,
            595 => Self::LBRACE_OptSemicolons_CreateAccessPolicySDLCommandsList_OptSemicolons_RBRACE,
            596 => Self::LBRACE_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAccessPolicySDLCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            597 => Self::CreateAccessPolicySDLCommandFull,
            598 => Self::CreateAccessPolicySDLCommandsList_OptSemicolons_CreateAccessPolicySDLCommandFull,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAccessPolicyStmt {
    fn from_id(id: usize) -> Self {
        match id {
            599 => Self::CREATE_ACCESS_POLICY_UnqualifiedPointerName_OptWhenBlock_AccessPolicyAction_AccessKindList_OptUsingBlock_OptCreateAccessPolicyCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAliasCommand {
    fn from_id(id: usize) -> Self {
        match id {
            600 => Self::AlterAnnotationValueStmt,
            601 => Self::CreateAnnotationValueStmt,
            602 => Self::SetFieldStmt,
            603 => Self::UsingStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAliasCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            604 => Self::CreateAliasCommand,
            605 => Self::LBRACE_CreateAliasCommandsList_OptSemicolons_RBRACE,
            606 => Self::LBRACE_OptSemicolons_RBRACE,
            607 => Self::LBRACE_Semicolons_CreateAliasCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAliasCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            608 => Self::CreateAliasCommand,
            609 => Self::CreateAliasCommandsList_Semicolons_CreateAliasCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAliasSDLCommandFull {
    fn from_id(id: usize) -> Self {
        match id {
            611 => Self::CreateAliasSDLCommandShort_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAliasSDLCommandShort {
    fn from_id(id: usize) -> Self {
        match id {
            612 => Self::SetAnnotation,
            613 => Self::SetField,
            614 => Self::Using,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAliasSDLCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            615 => Self::LBRACE_OptSemicolons_CreateAliasSDLCommandShort_RBRACE,
            616 => Self::LBRACE_OptSemicolons_CreateAliasSDLCommandsList_OptSemicolons_CreateAliasSDLCommandShort_RBRACE,
            617 => Self::LBRACE_OptSemicolons_CreateAliasSDLCommandsList_OptSemicolons_RBRACE,
            618 => Self::LBRACE_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAliasSDLCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            619 => Self::CreateAliasSDLCommandFull,
            620 => Self::CreateAliasSDLCommandsList_OptSemicolons_CreateAliasSDLCommandFull,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAliasSingleSDLCommandBlock {
    fn from_id(id: usize) -> Self {
        match id {
            622 => Self::CreateAliasSDLCommandShort,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAliasStmt {
    fn from_id(id: usize) -> Self {
        match id {
            623 => Self::CREATE_ALIAS_NodeName_CreateAliasCommandsBlock,
            624 => Self::CREATE_ALIAS_NodeName_ASSIGN_GenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAnnotationCommand {
    fn from_id(id: usize) -> Self {
        match id {
            625 => Self::CreateAnnotationValueStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAnnotationCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            626 => Self::LBRACE_CreateAnnotationCommandsList_OptSemicolons_RBRACE,
            627 => Self::LBRACE_OptSemicolons_RBRACE,
            628 => Self::LBRACE_Semicolons_CreateAnnotationCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAnnotationCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            629 => Self::CreateAnnotationCommand,
            630 => Self::CreateAnnotationCommandsList_Semicolons_CreateAnnotationCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAnnotationStmt {
    fn from_id(id: usize) -> Self {
        match id {
            631 => Self::CREATE_ABSTRACT_ANNOTATION_NodeName_OptCreateAnnotationCommandsBlock,
            632 => Self::CREATE_ABSTRACT_INHERITABLE_ANNOTATION_NodeName_OptCreateCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateAnnotationValueStmt {
    fn from_id(id: usize) -> Self {
        match id {
            633 => Self::CREATE_ANNOTATION_NodeName_ASSIGN_GenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateBranchStmt {
    fn from_id(id: usize) -> Self {
        match id {
            634 => Self::CREATE_EMPTY_BRANCH_DatabaseName,
            635 => Self::CREATE_DATA_BRANCH_DatabaseName_FROM_DatabaseName,
            636 => Self::CREATE_SCHEMA_BRANCH_DatabaseName_FROM_DatabaseName,
            637 => Self::CREATE_TEMPLATE_BRANCH_DatabaseName_FROM_DatabaseName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateCastCommand {
    fn from_id(id: usize) -> Self {
        match id {
            638 => Self::AlterAnnotationValueStmt,
            639 => Self::CastAllowedUse,
            640 => Self::CastCode,
            641 => Self::CreateAnnotationValueStmt,
            642 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateCastCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            643 => Self::CreateCastCommand,
            644 => Self::LBRACE_CreateCastCommandsList_OptSemicolons_RBRACE,
            645 => Self::LBRACE_OptSemicolons_RBRACE,
            646 => Self::LBRACE_Semicolons_CreateCastCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateCastCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            647 => Self::CreateCastCommand,
            648 => Self::CreateCastCommandsList_Semicolons_CreateCastCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateCastStmt {
    fn from_id(id: usize) -> Self {
        match id {
            649 => Self::CREATE_CAST_FROM_TypeName_TO_TypeName_CreateCastCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateCommand {
    fn from_id(id: usize) -> Self {
        match id {
            650 => Self::AlterAnnotationValueStmt,
            651 => Self::CreateAnnotationValueStmt,
            652 => Self::SetFieldStmt,
            653 => Self::UsingStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            654 => Self::LBRACE_CreateCommandsList_OptSemicolons_RBRACE,
            655 => Self::LBRACE_OptSemicolons_RBRACE,
            656 => Self::LBRACE_Semicolons_CreateCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            657 => Self::CreateCommand,
            658 => Self::CreateCommandsList_Semicolons_CreateCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcreteConstraintStmt {
    fn from_id(id: usize) -> Self {
        match id {
            659 => Self::CREATE_OptDelegated_CONSTRAINT_NodeName_OptConcreteConstraintArgList_OptOnExpr_OptExceptExpr_OptCreateCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcreteIndexSDLCommandFull {
    fn from_id(id: usize) -> Self {
        match id {
            661 => Self::CreateConcreteIndexSDLCommandShort_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcreteIndexSDLCommandShort {
    fn from_id(id: usize) -> Self {
        match id {
            662 => Self::SetAnnotation,
            663 => Self::SetField,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcreteIndexSDLCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            664 => Self::LBRACE_OptSemicolons_CreateConcreteIndexSDLCommandShort_RBRACE,
            665 => Self::LBRACE_OptSemicolons_CreateConcreteIndexSDLCommandsList_OptSemicolons_CreateConcreteIndexSDLCommandShort_RBRACE,
            666 => Self::LBRACE_OptSemicolons_CreateConcreteIndexSDLCommandsList_OptSemicolons_RBRACE,
            667 => Self::LBRACE_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcreteIndexSDLCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            668 => Self::CreateConcreteIndexSDLCommandFull,
            669 => Self::CreateConcreteIndexSDLCommandsList_OptSemicolons_CreateConcreteIndexSDLCommandFull,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcreteIndexStmt {
    fn from_id(id: usize) -> Self {
        match id {
            670 => Self::CREATE_OptDeferred_INDEX_OnExpr_OptExceptExpr_OptCreateCommandsBlock,
            671 => Self::CREATE_OptDeferred_INDEX_NodeName_OptIndexExtArgList_OnExpr_OptExceptExpr_OptCreateCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcreteLinkCommand {
    fn from_id(id: usize) -> Self {
        match id {
            672 => Self::AlterAnnotationValueStmt,
            673 => Self::CreateAnnotationValueStmt,
            674 => Self::CreateConcreteConstraintStmt,
            675 => Self::CreateConcreteIndexStmt,
            676 => Self::CreateConcretePropertyStmt,
            677 => Self::CreateRewriteStmt,
            678 => Self::CreateSimpleExtending,
            679 => Self::OnSourceDeleteStmt,
            680 => Self::OnTargetDeleteStmt,
            681 => Self::SetFieldStmt,
            682 => Self::SetRequiredInCreateStmt,
            683 => Self::UsingStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcreteLinkCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            684 => Self::LBRACE_CreateConcreteLinkCommandsList_OptSemicolons_RBRACE,
            685 => Self::LBRACE_OptSemicolons_RBRACE,
            686 => Self::LBRACE_Semicolons_CreateConcreteLinkCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcreteLinkCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            687 => Self::CreateConcreteLinkCommand,
            688 => Self::CreateConcreteLinkCommandsList_Semicolons_CreateConcreteLinkCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcreteLinkSDLCommandBlock {
    fn from_id(id: usize) -> Self {
        match id {
            689 => Self::ConcreteConstraintBlock,
            690 => Self::ConcreteIndexDeclarationBlock,
            691 => Self::ConcretePropertyBlock,
            692 => Self::ConcreteUnknownPointerBlock,
            693 => Self::RewriteDeclarationBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcreteLinkSDLCommandFull {
    fn from_id(id: usize) -> Self {
        match id {
            694 => Self::CreateConcreteLinkSDLCommandBlock,
            695 => Self::CreateConcreteLinkSDLCommandShort_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcreteLinkSDLCommandShort {
    fn from_id(id: usize) -> Self {
        match id {
            696 => Self::ConcreteConstraintShort,
            697 => Self::ConcreteIndexDeclarationShort,
            698 => Self::ConcretePropertyShort,
            699 => Self::ConcreteUnknownPointerShort,
            700 => Self::CreateSimpleExtending,
            701 => Self::OnSourceDeleteStmt,
            702 => Self::OnTargetDeleteStmt,
            703 => Self::RewriteDeclarationShort,
            704 => Self::SetAnnotation,
            705 => Self::SetField,
            706 => Self::Using,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcreteLinkSDLCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            707 => Self::LBRACE_OptSemicolons_CreateConcreteLinkSDLCommandShort_RBRACE,
            708 => Self::LBRACE_OptSemicolons_CreateConcreteLinkSDLCommandsList_OptSemicolons_CreateConcreteLinkSDLCommandShort_RBRACE,
            709 => Self::LBRACE_OptSemicolons_CreateConcreteLinkSDLCommandsList_OptSemicolons_RBRACE,
            710 => Self::LBRACE_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcreteLinkSDLCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            711 => Self::CreateConcreteLinkSDLCommandFull,
            712 => Self::CreateConcreteLinkSDLCommandsList_OptSemicolons_CreateConcreteLinkSDLCommandFull,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcreteLinkStmt {
    fn from_id(id: usize) -> Self {
        match id {
            713 => Self::CREATE_OptPtrQuals_LINK_UnqualifiedPointerName_ASSIGN_GenExpr,
            714 => Self::CREATE_OptPtrQuals_LINK_UnqualifiedPointerName_OptCreateConcreteLinkCommandsBlock,
            715 => Self::CREATE_OptPtrQuals_LINK_UnqualifiedPointerName_OptExtendingSimple_ARROW_FullTypeExpr_OptCreateConcreteLinkCommandsBlock,
            716 => Self::CREATE_OptPtrQuals_LINK_UnqualifiedPointerName_OptExtendingSimple_COLON_FullTypeExpr_OptCreateConcreteLinkCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcretePropertyCommand {
    fn from_id(id: usize) -> Self {
        match id {
            717 => Self::AlterAnnotationValueStmt,
            718 => Self::CreateAnnotationValueStmt,
            719 => Self::CreateConcreteConstraintStmt,
            720 => Self::CreateRewriteStmt,
            721 => Self::CreateSimpleExtending,
            722 => Self::SetFieldStmt,
            723 => Self::SetRequiredInCreateStmt,
            724 => Self::UsingStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcretePropertyCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            725 => Self::LBRACE_CreateConcretePropertyCommandsList_OptSemicolons_RBRACE,
            726 => Self::LBRACE_OptSemicolons_RBRACE,
            727 => Self::LBRACE_Semicolons_CreateConcretePropertyCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcretePropertyCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            728 => Self::CreateConcretePropertyCommand,
            729 => Self::CreateConcretePropertyCommandsList_Semicolons_CreateConcretePropertyCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcretePropertySDLCommandBlock {
    fn from_id(id: usize) -> Self {
        match id {
            730 => Self::ConcreteConstraintBlock,
            731 => Self::RewriteDeclarationBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcretePropertySDLCommandFull {
    fn from_id(id: usize) -> Self {
        match id {
            732 => Self::CreateConcretePropertySDLCommandBlock,
            733 => Self::CreateConcretePropertySDLCommandShort_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcretePropertySDLCommandShort {
    fn from_id(id: usize) -> Self {
        match id {
            734 => Self::ConcreteConstraintShort,
            735 => Self::CreateSimpleExtending,
            736 => Self::RewriteDeclarationShort,
            737 => Self::SetAnnotation,
            738 => Self::SetField,
            739 => Self::Using,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcretePropertySDLCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            740 => Self::LBRACE_OptSemicolons_CreateConcretePropertySDLCommandShort_RBRACE,
            741 => Self::LBRACE_OptSemicolons_CreateConcretePropertySDLCommandsList_OptSemicolons_CreateConcretePropertySDLCommandShort_RBRACE,
            742 => Self::LBRACE_OptSemicolons_CreateConcretePropertySDLCommandsList_OptSemicolons_RBRACE,
            743 => Self::LBRACE_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcretePropertySDLCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            744 => Self::CreateConcretePropertySDLCommandFull,
            745 => Self::CreateConcretePropertySDLCommandsList_OptSemicolons_CreateConcretePropertySDLCommandFull,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConcretePropertyStmt {
    fn from_id(id: usize) -> Self {
        match id {
            746 => Self::CREATE_OptPtrQuals_PROPERTY_UnqualifiedPointerName_ASSIGN_GenExpr,
            747 => Self::CREATE_OptPtrQuals_PROPERTY_UnqualifiedPointerName_OptCreateConcretePropertyCommandsBlock,
            748 => Self::CREATE_OptPtrQuals_PROPERTY_UnqualifiedPointerName_OptExtendingSimple_ARROW_FullTypeExpr_OptCreateConcretePropertyCommandsBlock,
            749 => Self::CREATE_OptPtrQuals_PROPERTY_UnqualifiedPointerName_OptExtendingSimple_COLON_FullTypeExpr_OptCreateConcretePropertyCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateConstraintStmt {
    fn from_id(id: usize) -> Self {
        match id {
            750 => Self::CREATE_ABSTRACT_CONSTRAINT_NodeName_OptOnExpr_OptExtendingSimple_OptCreateCommandsBlock,
            751 => Self::CREATE_ABSTRACT_CONSTRAINT_NodeName_CreateFunctionArgs_OptOnExpr_OptExtendingSimple_OptCreateCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateDatabaseCommand {
    fn from_id(id: usize) -> Self {
        match id {
            752 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateDatabaseCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            753 => Self::LBRACE_CreateDatabaseCommandsList_OptSemicolons_RBRACE,
            754 => Self::LBRACE_OptSemicolons_RBRACE,
            755 => Self::LBRACE_Semicolons_CreateDatabaseCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateDatabaseCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            756 => Self::CreateDatabaseCommand,
            757 => Self::CreateDatabaseCommandsList_Semicolons_CreateDatabaseCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateDatabaseStmt {
    fn from_id(id: usize) -> Self {
        match id {
            758 => Self::CREATE_DATABASE_DatabaseName_FROM_AnyNodeName_OptCreateDatabaseCommandsBlock,
            759 => Self::CREATE_DATABASE_DatabaseName_OptCreateDatabaseCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateExtensionCommand {
    fn from_id(id: usize) -> Self {
        match id {
            760 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateExtensionCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            761 => Self::LBRACE_CreateExtensionCommandsList_OptSemicolons_RBRACE,
            762 => Self::LBRACE_OptSemicolons_RBRACE,
            763 => Self::LBRACE_Semicolons_CreateExtensionCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateExtensionCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            764 => Self::CreateExtensionCommand,
            765 => Self::CreateExtensionCommandsList_Semicolons_CreateExtensionCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateExtensionPackageCommand {
    fn from_id(id: usize) -> Self {
        match id {
            766 => Self::NestedQLBlockStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateExtensionPackageCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            767 => Self::LBRACE_CreateExtensionPackageCommandsList_OptSemicolons_RBRACE,
            768 => Self::LBRACE_OptSemicolons_RBRACE,
            769 => Self::LBRACE_Semicolons_CreateExtensionPackageCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateExtensionPackageCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            770 => Self::CreateExtensionPackageCommand,
            771 => Self::CreateExtensionPackageCommandsList_Semicolons_CreateExtensionPackageCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateExtensionPackageMigrationStmt {
    fn from_id(id: usize) -> Self {
        match id {
            772 => Self::CREATE_EXTENSIONPACKAGE_ShortNodeName_MIGRATION_FROM_ExtensionVersion_TO_ExtensionVersion_OptCreateExtensionPackageCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateExtensionPackageStmt {
    fn from_id(id: usize) -> Self {
        match id {
            773 => Self::CREATE_EXTENSIONPACKAGE_ShortNodeName_ExtensionVersion_OptCreateExtensionPackageCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateExtensionStmt {
    fn from_id(id: usize) -> Self {
        match id {
            774 => Self::CREATE_EXTENSION_ShortNodeName_OptExtensionVersion_OptCreateExtensionCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateFunctionArgs {
    fn from_id(id: usize) -> Self {
        match id {
            775 => Self::LPAREN_FuncDeclArgs_RPAREN,
            776 => Self::LPAREN_RPAREN,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateFunctionCommand {
    fn from_id(id: usize) -> Self {
        match id {
            777 => Self::AlterAnnotationValueStmt,
            778 => Self::CreateAnnotationValueStmt,
            779 => Self::FromFunction,
            780 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateFunctionCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            781 => Self::CreateFunctionCommand,
            782 => Self::LBRACE_CreateFunctionCommandsList_OptSemicolons_RBRACE,
            783 => Self::LBRACE_OptSemicolons_RBRACE,
            784 => Self::LBRACE_Semicolons_CreateFunctionCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateFunctionCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            785 => Self::CreateFunctionCommand,
            786 => Self::CreateFunctionCommandsList_Semicolons_CreateFunctionCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateFunctionSDLCommandFull {
    fn from_id(id: usize) -> Self {
        match id {
            788 => Self::CreateFunctionSDLCommandShort_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateFunctionSDLCommandShort {
    fn from_id(id: usize) -> Self {
        match id {
            789 => Self::FromFunction,
            790 => Self::SetAnnotation,
            791 => Self::SetField,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateFunctionSDLCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            792 => Self::LBRACE_OptSemicolons_CreateFunctionSDLCommandShort_RBRACE,
            793 => Self::LBRACE_OptSemicolons_CreateFunctionSDLCommandsList_OptSemicolons_CreateFunctionSDLCommandShort_RBRACE,
            794 => Self::LBRACE_OptSemicolons_CreateFunctionSDLCommandsList_OptSemicolons_RBRACE,
            795 => Self::LBRACE_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateFunctionSDLCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            796 => Self::CreateFunctionSDLCommandFull,
            797 => Self::CreateFunctionSDLCommandsList_OptSemicolons_CreateFunctionSDLCommandFull,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateFunctionSingleSDLCommandBlock {
    fn from_id(id: usize) -> Self {
        match id {
            799 => Self::CreateFunctionSDLCommandShort,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateFunctionStmt {
    fn from_id(id: usize) -> Self {
        match id {
            800 => Self::CREATE_FUNCTION_NodeName_CreateFunctionArgs_ARROW_OptTypeQualifier_FunctionType_CreateFunctionCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateFutureStmt {
    fn from_id(id: usize) -> Self {
        match id {
            801 => Self::CREATE_FUTURE_ShortNodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateGlobalCommand {
    fn from_id(id: usize) -> Self {
        match id {
            802 => Self::CreateAnnotationValueStmt,
            803 => Self::SetFieldStmt,
            804 => Self::UsingStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateGlobalCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            805 => Self::LBRACE_CreateGlobalCommandsList_OptSemicolons_RBRACE,
            806 => Self::LBRACE_OptSemicolons_RBRACE,
            807 => Self::LBRACE_Semicolons_CreateGlobalCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateGlobalCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            808 => Self::CreateGlobalCommand,
            809 => Self::CreateGlobalCommandsList_Semicolons_CreateGlobalCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateGlobalSDLCommandFull {
    fn from_id(id: usize) -> Self {
        match id {
            811 => Self::CreateGlobalSDLCommandShort_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateGlobalSDLCommandShort {
    fn from_id(id: usize) -> Self {
        match id {
            812 => Self::SetAnnotation,
            813 => Self::SetField,
            814 => Self::Using,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateGlobalSDLCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            815 => Self::LBRACE_OptSemicolons_CreateGlobalSDLCommandShort_RBRACE,
            816 => Self::LBRACE_OptSemicolons_CreateGlobalSDLCommandsList_OptSemicolons_CreateGlobalSDLCommandShort_RBRACE,
            817 => Self::LBRACE_OptSemicolons_CreateGlobalSDLCommandsList_OptSemicolons_RBRACE,
            818 => Self::LBRACE_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateGlobalSDLCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            819 => Self::CreateGlobalSDLCommandFull,
            820 => Self::CreateGlobalSDLCommandsList_OptSemicolons_CreateGlobalSDLCommandFull,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateGlobalStmt {
    fn from_id(id: usize) -> Self {
        match id {
            821 => Self::CREATE_OptPtrQuals_GLOBAL_NodeName_ASSIGN_GenExpr,
            822 => Self::CREATE_OptPtrQuals_GLOBAL_NodeName_OptCreateConcretePropertyCommandsBlock,
            823 => Self::CREATE_OptPtrQuals_GLOBAL_NodeName_ARROW_FullTypeExpr_OptCreateGlobalCommandsBlock,
            824 => Self::CREATE_OptPtrQuals_GLOBAL_NodeName_COLON_FullTypeExpr_OptCreateGlobalCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateIndexCommand {
    fn from_id(id: usize) -> Self {
        match id {
            825 => Self::AlterAnnotationValueStmt,
            826 => Self::CreateAnnotationValueStmt,
            827 => Self::SetFieldStmt,
            828 => Self::UsingStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateIndexCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            829 => Self::LBRACE_CreateIndexCommandsList_OptSemicolons_RBRACE,
            830 => Self::LBRACE_OptSemicolons_RBRACE,
            831 => Self::LBRACE_Semicolons_CreateIndexCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateIndexCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            832 => Self::CreateIndexCommand,
            833 => Self::CreateIndexCommandsList_Semicolons_CreateIndexCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateIndexMatchCommand {
    fn from_id(id: usize) -> Self {
        match id {
            834 => Self::CreateAnnotationValueStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateIndexMatchCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            835 => Self::LBRACE_CreateIndexMatchCommandsList_OptSemicolons_RBRACE,
            836 => Self::LBRACE_OptSemicolons_RBRACE,
            837 => Self::LBRACE_Semicolons_CreateIndexMatchCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateIndexMatchCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            838 => Self::CreateIndexMatchCommand,
            839 => Self::CreateIndexMatchCommandsList_Semicolons_CreateIndexMatchCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateIndexMatchStmt {
    fn from_id(id: usize) -> Self {
        match id {
            840 => Self::CREATE_INDEX_MATCH_FOR_TypeName_USING_NodeName_OptCreateIndexMatchCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateIndexSDLCommandFull {
    fn from_id(id: usize) -> Self {
        match id {
            842 => Self::CreateIndexSDLCommandShort_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateIndexSDLCommandShort {
    fn from_id(id: usize) -> Self {
        match id {
            843 => Self::SetAnnotation,
            844 => Self::SetField,
            845 => Self::Using,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateIndexSDLCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            846 => Self::LBRACE_OptSemicolons_CreateIndexSDLCommandShort_RBRACE,
            847 => Self::LBRACE_OptSemicolons_CreateIndexSDLCommandsList_OptSemicolons_CreateIndexSDLCommandShort_RBRACE,
            848 => Self::LBRACE_OptSemicolons_CreateIndexSDLCommandsList_OptSemicolons_RBRACE,
            849 => Self::LBRACE_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateIndexSDLCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            850 => Self::CreateIndexSDLCommandFull,
            851 => Self::CreateIndexSDLCommandsList_OptSemicolons_CreateIndexSDLCommandFull,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateIndexStmt {
    fn from_id(id: usize) -> Self {
        match id {
            852 => Self::CREATE_ABSTRACT_INDEX_NodeName_OptExtendingSimple_OptCreateIndexCommandsBlock,
            853 => Self::CREATE_ABSTRACT_INDEX_NodeName_IndexExtArgList_OptExtendingSimple_OptCreateIndexCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateLinkCommand {
    fn from_id(id: usize) -> Self {
        match id {
            854 => Self::AlterAnnotationValueStmt,
            855 => Self::CreateAnnotationValueStmt,
            856 => Self::CreateConcreteConstraintStmt,
            857 => Self::CreateConcreteIndexStmt,
            858 => Self::CreateConcretePropertyStmt,
            859 => Self::CreateRewriteStmt,
            860 => Self::CreateSimpleExtending,
            861 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateLinkCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            862 => Self::LBRACE_CreateLinkCommandsList_OptSemicolons_RBRACE,
            863 => Self::LBRACE_OptSemicolons_RBRACE,
            864 => Self::LBRACE_Semicolons_CreateLinkCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateLinkCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            865 => Self::CreateLinkCommand,
            866 => Self::CreateLinkCommandsList_Semicolons_CreateLinkCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateLinkSDLCommandBlock {
    fn from_id(id: usize) -> Self {
        match id {
            867 => Self::ConcreteConstraintBlock,
            868 => Self::ConcreteIndexDeclarationBlock,
            869 => Self::ConcretePropertyBlock,
            870 => Self::ConcreteUnknownPointerBlock,
            871 => Self::RewriteDeclarationBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateLinkSDLCommandFull {
    fn from_id(id: usize) -> Self {
        match id {
            872 => Self::CreateLinkSDLCommandBlock,
            873 => Self::CreateLinkSDLCommandShort_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateLinkSDLCommandShort {
    fn from_id(id: usize) -> Self {
        match id {
            874 => Self::ConcreteConstraintShort,
            875 => Self::ConcreteIndexDeclarationShort,
            876 => Self::ConcretePropertyShort,
            877 => Self::ConcreteUnknownPointerShort,
            878 => Self::CreateSimpleExtending,
            879 => Self::RewriteDeclarationShort,
            880 => Self::SetAnnotation,
            881 => Self::SetField,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateLinkSDLCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            882 => Self::LBRACE_OptSemicolons_CreateLinkSDLCommandShort_RBRACE,
            883 => Self::LBRACE_OptSemicolons_CreateLinkSDLCommandsList_OptSemicolons_CreateLinkSDLCommandShort_RBRACE,
            884 => Self::LBRACE_OptSemicolons_CreateLinkSDLCommandsList_OptSemicolons_RBRACE,
            885 => Self::LBRACE_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateLinkSDLCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            886 => Self::CreateLinkSDLCommandFull,
            887 => Self::CreateLinkSDLCommandsList_OptSemicolons_CreateLinkSDLCommandFull,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateLinkStmt {
    fn from_id(id: usize) -> Self {
        match id {
            888 => Self::CREATE_ABSTRACT_LINK_PtrNodeName_OptExtendingSimple_OptCreateLinkCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateMigrationCommand {
    fn from_id(id: usize) -> Self {
        match id {
            889 => Self::NestedQLBlockStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateMigrationCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            890 => Self::LBRACE_CreateMigrationCommandsList_OptSemicolons_RBRACE,
            891 => Self::LBRACE_OptSemicolons_RBRACE,
            892 => Self::LBRACE_Semicolons_CreateMigrationCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateMigrationCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            893 => Self::CreateMigrationCommand,
            894 => Self::CreateMigrationCommandsList_Semicolons_CreateMigrationCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateMigrationStmt {
    fn from_id(id: usize) -> Self {
        match id {
            895 => Self::CREATE_APPLIED_MIGRATION_OptMigrationNameParentName_OptCreateMigrationCommandsBlock,
            896 => Self::CREATE_MIGRATION_OptMigrationNameParentName_OptCreateMigrationCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateModuleStmt {
    fn from_id(id: usize) -> Self {
        match id {
            897 => Self::CREATE_MODULE_ModuleName_OptIfNotExists_OptCreateCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateObjectTypeCommand {
    fn from_id(id: usize) -> Self {
        match id {
            898 => Self::AlterAccessPolicyStmt,
            899 => Self::AlterAnnotationValueStmt,
            900 => Self::AlterConcreteConstraintStmt,
            901 => Self::AlterConcreteIndexStmt,
            902 => Self::AlterConcreteLinkStmt,
            903 => Self::AlterConcretePropertyStmt,
            904 => Self::AlterTriggerStmt,
            905 => Self::CreateAccessPolicyStmt,
            906 => Self::CreateAnnotationValueStmt,
            907 => Self::CreateConcreteConstraintStmt,
            908 => Self::CreateConcreteIndexStmt,
            909 => Self::CreateConcreteLinkStmt,
            910 => Self::CreateConcretePropertyStmt,
            911 => Self::CreateTriggerStmt,
            912 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateObjectTypeCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            913 => Self::LBRACE_CreateObjectTypeCommandsList_OptSemicolons_RBRACE,
            914 => Self::LBRACE_OptSemicolons_RBRACE,
            915 => Self::LBRACE_Semicolons_CreateObjectTypeCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateObjectTypeCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            916 => Self::CreateObjectTypeCommand,
            917 => Self::CreateObjectTypeCommandsList_Semicolons_CreateObjectTypeCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateObjectTypeSDLCommandBlock {
    fn from_id(id: usize) -> Self {
        match id {
            918 => Self::AccessPolicyDeclarationBlock,
            919 => Self::ConcreteConstraintBlock,
            920 => Self::ConcreteIndexDeclarationBlock,
            921 => Self::ConcreteLinkBlock,
            922 => Self::ConcretePropertyBlock,
            923 => Self::ConcreteUnknownPointerBlock,
            924 => Self::TriggerDeclarationBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateObjectTypeSDLCommandFull {
    fn from_id(id: usize) -> Self {
        match id {
            925 => Self::CreateObjectTypeSDLCommandBlock,
            926 => Self::CreateObjectTypeSDLCommandShort_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateObjectTypeSDLCommandShort {
    fn from_id(id: usize) -> Self {
        match id {
            927 => Self::AccessPolicyDeclarationShort,
            928 => Self::ConcreteConstraintShort,
            929 => Self::ConcreteIndexDeclarationShort,
            930 => Self::ConcreteLinkShort,
            931 => Self::ConcretePropertyShort,
            932 => Self::ConcreteUnknownPointerObjectShort,
            933 => Self::ConcreteUnknownPointerShort,
            934 => Self::SetAnnotation,
            935 => Self::TriggerDeclarationShort,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateObjectTypeSDLCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            936 => Self::LBRACE_OptSemicolons_CreateObjectTypeSDLCommandShort_RBRACE,
            937 => Self::LBRACE_OptSemicolons_CreateObjectTypeSDLCommandsList_OptSemicolons_CreateObjectTypeSDLCommandShort_RBRACE,
            938 => Self::LBRACE_OptSemicolons_CreateObjectTypeSDLCommandsList_OptSemicolons_RBRACE,
            939 => Self::LBRACE_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateObjectTypeSDLCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            940 => Self::CreateObjectTypeSDLCommandFull,
            941 => Self::CreateObjectTypeSDLCommandsList_OptSemicolons_CreateObjectTypeSDLCommandFull,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateObjectTypeStmt {
    fn from_id(id: usize) -> Self {
        match id {
            942 => Self::CREATE_ABSTRACT_TYPE_NodeName_OptExtendingSimple_OptCreateObjectTypeCommandsBlock,
            943 => Self::CREATE_TYPE_NodeName_OptExtendingSimple_OptCreateObjectTypeCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateOperatorCommand {
    fn from_id(id: usize) -> Self {
        match id {
            944 => Self::AlterAnnotationValueStmt,
            945 => Self::CreateAnnotationValueStmt,
            946 => Self::OperatorCode,
            947 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateOperatorCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            948 => Self::CreateOperatorCommand,
            949 => Self::LBRACE_CreateOperatorCommandsList_OptSemicolons_RBRACE,
            950 => Self::LBRACE_OptSemicolons_RBRACE,
            951 => Self::LBRACE_Semicolons_CreateOperatorCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateOperatorCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            952 => Self::CreateOperatorCommand,
            953 => Self::CreateOperatorCommandsList_Semicolons_CreateOperatorCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateOperatorStmt {
    fn from_id(id: usize) -> Self {
        match id {
            954 => Self::CREATE_ABSTRACT_OperatorKind_OPERATOR_NodeName_CreateFunctionArgs_ARROW_OptTypeQualifier_FunctionType_OptCreateOperatorCommandsBlock,
            955 => Self::CREATE_OperatorKind_OPERATOR_NodeName_CreateFunctionArgs_ARROW_OptTypeQualifier_FunctionType_CreateOperatorCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePermissionCommand {
    fn from_id(id: usize) -> Self {
        match id {
            956 => Self::CreateAnnotationValueStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePermissionCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            957 => Self::LBRACE_CreatePermissionCommandsList_OptSemicolons_RBRACE,
            958 => Self::LBRACE_OptSemicolons_RBRACE,
            959 => Self::LBRACE_Semicolons_CreatePermissionCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePermissionCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            960 => Self::CreatePermissionCommand,
            961 => Self::CreatePermissionCommandsList_Semicolons_CreatePermissionCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePermissionSDLCommandFull {
    fn from_id(id: usize) -> Self {
        match id {
            963 => Self::CreatePermissionSDLCommandShort_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePermissionSDLCommandShort {
    fn from_id(id: usize) -> Self {
        match id {
            964 => Self::SetAnnotation,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePermissionSDLCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            965 => Self::LBRACE_OptSemicolons_CreatePermissionSDLCommandShort_RBRACE,
            966 => Self::LBRACE_OptSemicolons_CreatePermissionSDLCommandsList_OptSemicolons_CreatePermissionSDLCommandShort_RBRACE,
            967 => Self::LBRACE_OptSemicolons_CreatePermissionSDLCommandsList_OptSemicolons_RBRACE,
            968 => Self::LBRACE_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePermissionSDLCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            969 => Self::CreatePermissionSDLCommandFull,
            970 => Self::CreatePermissionSDLCommandsList_OptSemicolons_CreatePermissionSDLCommandFull,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePermissionStmt {
    fn from_id(id: usize) -> Self {
        match id {
            971 => Self::CREATE_PERMISSION_NodeName_OptCreatePermissionCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePropertyCommand {
    fn from_id(id: usize) -> Self {
        match id {
            972 => Self::AlterAnnotationValueStmt,
            973 => Self::CreateAnnotationValueStmt,
            974 => Self::CreateSimpleExtending,
            975 => Self::SetFieldStmt,
            976 => Self::UsingStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePropertyCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            977 => Self::LBRACE_CreatePropertyCommandsList_OptSemicolons_RBRACE,
            978 => Self::LBRACE_OptSemicolons_RBRACE,
            979 => Self::LBRACE_Semicolons_CreatePropertyCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePropertyCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            980 => Self::CreatePropertyCommand,
            981 => Self::CreatePropertyCommandsList_Semicolons_CreatePropertyCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePropertySDLCommandFull {
    fn from_id(id: usize) -> Self {
        match id {
            983 => Self::CreatePropertySDLCommandShort_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePropertySDLCommandShort {
    fn from_id(id: usize) -> Self {
        match id {
            984 => Self::CreateSimpleExtending,
            985 => Self::SetAnnotation,
            986 => Self::SetField,
            987 => Self::Using,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePropertySDLCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            988 => Self::LBRACE_OptSemicolons_CreatePropertySDLCommandShort_RBRACE,
            989 => Self::LBRACE_OptSemicolons_CreatePropertySDLCommandsList_OptSemicolons_CreatePropertySDLCommandShort_RBRACE,
            990 => Self::LBRACE_OptSemicolons_CreatePropertySDLCommandsList_OptSemicolons_RBRACE,
            991 => Self::LBRACE_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePropertySDLCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            992 => Self::CreatePropertySDLCommandFull,
            993 => Self::CreatePropertySDLCommandsList_OptSemicolons_CreatePropertySDLCommandFull,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePropertyStmt {
    fn from_id(id: usize) -> Self {
        match id {
            994 => Self::CREATE_ABSTRACT_PROPERTY_PtrNodeName_OptExtendingSimple_OptCreatePropertyCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePseudoTypeCommand {
    fn from_id(id: usize) -> Self {
        match id {
            995 => Self::AlterAnnotationValueStmt,
            996 => Self::CreateAnnotationValueStmt,
            997 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePseudoTypeCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            998 => Self::LBRACE_CreatePseudoTypeCommandsList_OptSemicolons_RBRACE,
            999 => Self::LBRACE_OptSemicolons_RBRACE,
            1000 => Self::LBRACE_Semicolons_CreatePseudoTypeCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePseudoTypeCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            1001 => Self::CreatePseudoTypeCommand,
            1002 => Self::CreatePseudoTypeCommandsList_Semicolons_CreatePseudoTypeCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreatePseudoTypeStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1003 => Self::CREATE_PSEUDO_TYPE_NodeName_OptCreatePseudoTypeCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateRewriteCommand {
    fn from_id(id: usize) -> Self {
        match id {
            1004 => Self::CreateAnnotationValueStmt,
            1005 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateRewriteCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1006 => Self::LBRACE_CreateRewriteCommandsList_OptSemicolons_RBRACE,
            1007 => Self::LBRACE_OptSemicolons_RBRACE,
            1008 => Self::LBRACE_Semicolons_CreateRewriteCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateRewriteCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            1009 => Self::CreateRewriteCommand,
            1010 => Self::CreateRewriteCommandsList_Semicolons_CreateRewriteCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateRewriteSDLCommandFull {
    fn from_id(id: usize) -> Self {
        match id {
            1012 => Self::CreateRewriteSDLCommandShort_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateRewriteSDLCommandShort {
    fn from_id(id: usize) -> Self {
        match id {
            1013 => Self::SetAnnotation,
            1014 => Self::SetField,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateRewriteSDLCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1015 => Self::LBRACE_OptSemicolons_CreateRewriteSDLCommandShort_RBRACE,
            1016 => Self::LBRACE_OptSemicolons_CreateRewriteSDLCommandsList_OptSemicolons_CreateRewriteSDLCommandShort_RBRACE,
            1017 => Self::LBRACE_OptSemicolons_CreateRewriteSDLCommandsList_OptSemicolons_RBRACE,
            1018 => Self::LBRACE_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateRewriteSDLCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            1019 => Self::CreateRewriteSDLCommandFull,
            1020 => Self::CreateRewriteSDLCommandsList_OptSemicolons_CreateRewriteSDLCommandFull,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateRewriteStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1021 => Self::CREATE_REWRITE_RewriteKindList_USING_ParenExpr_OptCreateRewriteCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateRoleCommand {
    fn from_id(id: usize) -> Self {
        match id {
            1022 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateRoleCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1023 => Self::LBRACE_CreateRoleCommandsList_OptSemicolons_RBRACE,
            1024 => Self::LBRACE_OptSemicolons_RBRACE,
            1025 => Self::LBRACE_Semicolons_CreateRoleCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateRoleCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            1026 => Self::CreateRoleCommand,
            1027 => Self::CreateRoleCommandsList_Semicolons_CreateRoleCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateRoleStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1028 => Self::CREATE_OptSuperuser_ROLE_ShortNodeName_OptShortExtending_OptIfNotExists_OptCreateRoleCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateSDLCommandFull {
    fn from_id(id: usize) -> Self {
        match id {
            1030 => Self::CreateSDLCommandShort_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateSDLCommandShort {
    fn from_id(id: usize) -> Self {
        match id {
            1031 => Self::SetAnnotation,
            1032 => Self::SetField,
            1033 => Self::Using,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateSDLCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1034 => Self::LBRACE_OptSemicolons_CreateSDLCommandShort_RBRACE,
            1035 => Self::LBRACE_OptSemicolons_CreateSDLCommandsList_OptSemicolons_CreateSDLCommandShort_RBRACE,
            1036 => Self::LBRACE_OptSemicolons_CreateSDLCommandsList_OptSemicolons_RBRACE,
            1037 => Self::LBRACE_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateSDLCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            1038 => Self::CreateSDLCommandFull,
            1039 => Self::CreateSDLCommandsList_OptSemicolons_CreateSDLCommandFull,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateScalarTypeCommand {
    fn from_id(id: usize) -> Self {
        match id {
            1040 => Self::AlterAnnotationValueStmt,
            1041 => Self::CreateAnnotationValueStmt,
            1042 => Self::CreateConcreteConstraintStmt,
            1043 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateScalarTypeCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1044 => Self::LBRACE_CreateScalarTypeCommandsList_OptSemicolons_RBRACE,
            1045 => Self::LBRACE_OptSemicolons_RBRACE,
            1046 => Self::LBRACE_Semicolons_CreateScalarTypeCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateScalarTypeCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            1047 => Self::CreateScalarTypeCommand,
            1048 => Self::CreateScalarTypeCommandsList_Semicolons_CreateScalarTypeCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateScalarTypeSDLCommandBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1049 => Self::ConcreteConstraintBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateScalarTypeSDLCommandFull {
    fn from_id(id: usize) -> Self {
        match id {
            1050 => Self::CreateScalarTypeSDLCommandBlock,
            1051 => Self::CreateScalarTypeSDLCommandShort_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateScalarTypeSDLCommandShort {
    fn from_id(id: usize) -> Self {
        match id {
            1052 => Self::ConcreteConstraintShort,
            1053 => Self::SetAnnotation,
            1054 => Self::SetField,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateScalarTypeSDLCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1055 => Self::LBRACE_OptSemicolons_CreateScalarTypeSDLCommandShort_RBRACE,
            1056 => Self::LBRACE_OptSemicolons_CreateScalarTypeSDLCommandsList_OptSemicolons_CreateScalarTypeSDLCommandShort_RBRACE,
            1057 => Self::LBRACE_OptSemicolons_CreateScalarTypeSDLCommandsList_OptSemicolons_RBRACE,
            1058 => Self::LBRACE_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateScalarTypeSDLCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            1059 => Self::CreateScalarTypeSDLCommandFull,
            1060 => Self::CreateScalarTypeSDLCommandsList_OptSemicolons_CreateScalarTypeSDLCommandFull,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateScalarTypeStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1061 => Self::CREATE_ABSTRACT_SCALAR_TYPE_NodeName_OptExtending_OptCreateScalarTypeCommandsBlock,
            1062 => Self::CREATE_FINAL_SCALAR_TYPE_NodeName_OptExtending_OptCreateScalarTypeCommandsBlock,
            1063 => Self::CREATE_SCALAR_TYPE_NodeName_OptExtending_OptCreateScalarTypeCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateSimpleExtending {
    fn from_id(id: usize) -> Self {
        match id {
            1064 => Self::EXTENDING_SimpleTypeNameList,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateTriggerCommand {
    fn from_id(id: usize) -> Self {
        match id {
            1065 => Self::CreateAnnotationValueStmt,
            1066 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateTriggerCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1067 => Self::LBRACE_CreateTriggerCommandsList_OptSemicolons_RBRACE,
            1068 => Self::LBRACE_OptSemicolons_RBRACE,
            1069 => Self::LBRACE_Semicolons_CreateTriggerCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateTriggerCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            1070 => Self::CreateTriggerCommand,
            1071 => Self::CreateTriggerCommandsList_Semicolons_CreateTriggerCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateTriggerSDLCommandFull {
    fn from_id(id: usize) -> Self {
        match id {
            1073 => Self::CreateTriggerSDLCommandShort_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateTriggerSDLCommandShort {
    fn from_id(id: usize) -> Self {
        match id {
            1074 => Self::SetAnnotation,
            1075 => Self::SetField,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateTriggerSDLCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1076 => Self::LBRACE_OptSemicolons_CreateTriggerSDLCommandShort_RBRACE,
            1077 => Self::LBRACE_OptSemicolons_CreateTriggerSDLCommandsList_OptSemicolons_CreateTriggerSDLCommandShort_RBRACE,
            1078 => Self::LBRACE_OptSemicolons_CreateTriggerSDLCommandsList_OptSemicolons_RBRACE,
            1079 => Self::LBRACE_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateTriggerSDLCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            1080 => Self::CreateTriggerSDLCommandFull,
            1081 => Self::CreateTriggerSDLCommandsList_OptSemicolons_CreateTriggerSDLCommandFull,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::CreateTriggerStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1082 => Self::CREATE_TRIGGER_UnqualifiedPointerName_TriggerTiming_TriggerKindList_FOR_TriggerScope_OptWhenBlock_DO_ParenExpr_OptCreateTriggerCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DDLStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1083 => Self::BranchStmt,
            1084 => Self::DatabaseStmt,
            1085 => Self::ExtensionPackageStmt,
            1086 => Self::MigrationStmt,
            1087 => Self::OptWithDDLStmt,
            1088 => Self::RoleStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DDLWithBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1089 => Self::WithBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DatabaseName {
    fn from_id(id: usize) -> Self {
        match id {
            1090 => Self::Identifier,
            1091 => Self::ReservedKeyword,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DatabaseStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1092 => Self::AlterDatabaseStmt,
            1093 => Self::CreateDatabaseStmt,
            1094 => Self::DropDatabaseStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DescribeFormat {
    fn from_id(id: usize) -> Self {
        match id {
            1095 => Self::AS_DDL,
            1096 => Self::AS_JSON,
            1097 => Self::AS_SDL,
            1098 => Self::AS_TEXT,
            1099 => Self::AS_TEXT_VERBOSE,
            1100 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DescribeStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1101 => Self::DESCRIBE_CURRENT_BRANCH_CONFIG_DescribeFormat,
            1102 => Self::DESCRIBE_CURRENT_DATABASE_CONFIG_DescribeFormat,
            1103 => Self::DESCRIBE_CURRENT_MIGRATION_DescribeFormat,
            1104 => Self::DESCRIBE_INSTANCE_CONFIG_DescribeFormat,
            1105 => Self::DESCRIBE_OBJECT_NodeName_DescribeFormat,
            1106 => Self::DESCRIBE_ROLES_DescribeFormat,
            1107 => Self::DESCRIBE_SCHEMA_DescribeFormat,
            1108 => Self::DESCRIBE_SYSTEM_CONFIG_DescribeFormat,
            1109 => Self::DESCRIBE_SchemaItem_DescribeFormat,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DotName {
    fn from_id(id: usize) -> Self {
        match id {
            1110 => Self::DottedIdents,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DottedIdents {
    fn from_id(id: usize) -> Self {
        match id {
            1111 => Self::AnyIdentifier,
            1112 => Self::DottedIdents_DOT_AnyIdentifier,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropAccessPolicyStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1113 => Self::DROP_ACCESS_POLICY_UnqualifiedPointerName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropAliasStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1114 => Self::DROP_ALIAS_NodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropAnnotationStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1115 => Self::DROP_ABSTRACT_ANNOTATION_NodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropAnnotationValueStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1116 => Self::DROP_ANNOTATION_NodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropBranchStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1117 => Self::DROP_BRANCH_DatabaseName_BranchOptions,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropCastStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1118 => Self::DROP_CAST_FROM_TypeName_TO_TypeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropConcreteConstraintStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1119 => Self::DROP_CONSTRAINT_NodeName_OptConcreteConstraintArgList_OptOnExpr_OptExceptExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropConcreteIndexCommand {
    fn from_id(id: usize) -> Self {
        match id {
            1120 => Self::SetFieldStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropConcreteIndexCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1121 => Self::LBRACE_DropConcreteIndexCommandsList_OptSemicolons_RBRACE,
            1122 => Self::LBRACE_OptSemicolons_RBRACE,
            1123 => Self::LBRACE_Semicolons_DropConcreteIndexCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropConcreteIndexCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            1124 => Self::DropConcreteIndexCommand,
            1125 => Self::DropConcreteIndexCommandsList_Semicolons_DropConcreteIndexCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropConcreteIndexStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1126 => Self::DROP_INDEX_OnExpr_OptExceptExpr_OptDropConcreteIndexCommandsBlock,
            1127 => Self::DROP_INDEX_NodeName_OptIndexExtArgList_OnExpr_OptExceptExpr_OptDropConcreteIndexCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropConcreteLinkCommand {
    fn from_id(id: usize) -> Self {
        match id {
            1128 => Self::DropConcreteConstraintStmt,
            1129 => Self::DropConcreteIndexStmt,
            1130 => Self::DropConcretePropertyStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropConcreteLinkCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1131 => Self::LBRACE_DropConcreteLinkCommandsList_OptSemicolons_RBRACE,
            1132 => Self::LBRACE_OptSemicolons_RBRACE,
            1133 => Self::LBRACE_Semicolons_DropConcreteLinkCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropConcreteLinkCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            1134 => Self::DropConcreteLinkCommand,
            1135 => Self::DropConcreteLinkCommandsList_Semicolons_DropConcreteLinkCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropConcreteLinkStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1136 => Self::DROP_LINK_UnqualifiedPointerName_OptDropConcreteLinkCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropConcretePropertyStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1137 => Self::DROP_PROPERTY_UnqualifiedPointerName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropConstraintStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1138 => Self::DROP_ABSTRACT_CONSTRAINT_NodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropDatabaseStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1139 => Self::DROP_DATABASE_DatabaseName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropExtensionPackageMigrationStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1140 => Self::DROP_EXTENSIONPACKAGE_ShortNodeName_MIGRATION_FROM_ExtensionVersion_TO_ExtensionVersion,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropExtensionPackageStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1141 => Self::DROP_EXTENSIONPACKAGE_ShortNodeName_ExtensionVersion,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropExtensionStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1142 => Self::DROP_EXTENSION_ShortNodeName_OptExtensionVersion,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropFunctionStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1143 => Self::DROP_FUNCTION_NodeName_CreateFunctionArgs,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropFutureStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1144 => Self::DROP_FUTURE_ShortNodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropGlobalStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1145 => Self::DROP_GLOBAL_NodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropIndexMatchStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1146 => Self::DROP_INDEX_MATCH_FOR_TypeName_USING_NodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropIndexStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1147 => Self::DROP_ABSTRACT_INDEX_NodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropLinkCommand {
    fn from_id(id: usize) -> Self {
        match id {
            1148 => Self::DropConcreteConstraintStmt,
            1149 => Self::DropConcreteIndexStmt,
            1150 => Self::DropConcretePropertyStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropLinkCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1151 => Self::LBRACE_DropLinkCommandsList_OptSemicolons_RBRACE,
            1152 => Self::LBRACE_OptSemicolons_RBRACE,
            1153 => Self::LBRACE_Semicolons_DropLinkCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropLinkCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            1154 => Self::DropLinkCommand,
            1155 => Self::DropLinkCommandsList_Semicolons_DropLinkCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropLinkStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1156 => Self::DROP_ABSTRACT_LINK_PtrNodeName_OptDropLinkCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropMigrationStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1157 => Self::DROP_MIGRATION_NodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropModuleStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1158 => Self::DROP_MODULE_ModuleName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropObjectTypeCommand {
    fn from_id(id: usize) -> Self {
        match id {
            1159 => Self::DropConcreteConstraintStmt,
            1160 => Self::DropConcreteIndexStmt,
            1161 => Self::DropConcreteLinkStmt,
            1162 => Self::DropConcretePropertyStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropObjectTypeCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1163 => Self::LBRACE_DropObjectTypeCommandsList_OptSemicolons_RBRACE,
            1164 => Self::LBRACE_OptSemicolons_RBRACE,
            1165 => Self::LBRACE_Semicolons_DropObjectTypeCommandsList_OptSemicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropObjectTypeCommandsList {
    fn from_id(id: usize) -> Self {
        match id {
            1166 => Self::DropObjectTypeCommand,
            1167 => Self::DropObjectTypeCommandsList_Semicolons_DropObjectTypeCommand,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropObjectTypeStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1168 => Self::DROP_TYPE_NodeName_OptDropObjectTypeCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropOperatorStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1169 => Self::DROP_OperatorKind_OPERATOR_NodeName_CreateFunctionArgs,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropPermissionStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1170 => Self::DROP_PERMISSION_NodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropPropertyStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1171 => Self::DROP_ABSTRACT_PROPERTY_PtrNodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropRewriteStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1172 => Self::DROP_REWRITE_RewriteKindList,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropRoleStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1173 => Self::DROP_ROLE_ShortNodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropScalarTypeStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1174 => Self::DROP_SCALAR_TYPE_NodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::DropTriggerStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1175 => Self::DROP_TRIGGER_UnqualifiedPointerName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::EdgeQLBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1176 => Self::OptSemicolons,
            1177 => Self::StatementBlock_OptSemicolons,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::EdgeQLGrammar {
    fn from_id(id: usize) -> Self {
        match id {
            1178 => Self::STARTBLOCK_EdgeQLBlock_EOI,
            1179 => Self::STARTEXTENSION_CreateExtensionPackageCommandsBlock_EOI,
            1180 => Self::STARTFRAGMENT_ExprStmt_EOI,
            1181 => Self::STARTFRAGMENT_Expr_EOI,
            1182 => Self::STARTMIGRATION_CreateMigrationCommandsBlock_EOI,
            1183 => Self::STARTSDLDOCUMENT_SDLDocument_EOI,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::Expr {
    fn from_id(id: usize) -> Self {
        match id {
            1184 => Self::BaseAtomicExpr,
            1185 => Self::DETACHED_Expr,
            1186 => Self::DISTINCT_Expr,
            1187 => Self::EXISTS_Expr,
            1188 => Self::Expr_AND_Expr,
            1189 => Self::Expr_CIRCUMFLEX_Expr,
            1190 => Self::Expr_CompareOp_Expr_P_COMPARE_OP,
            1191 => Self::Expr_DOUBLEPLUS_Expr,
            1192 => Self::Expr_DOUBLEQMARK_Expr_P_DOUBLEQMARK_OP,
            1193 => Self::Expr_DOUBLESLASH_Expr,
            1194 => Self::Expr_EXCEPT_Expr,
            1195 => Self::Expr_IF_Expr_ELSE_Expr,
            1196 => Self::Expr_ILIKE_Expr,
            1197 => Self::Expr_INTERSECT_Expr,
            1198 => Self::Expr_IN_Expr,
            1199 => Self::Expr_IS_NOT_TypeExpr_P_IS,
            1200 => Self::Expr_IS_TypeExpr,
            1201 => Self::Expr_IndirectionEl,
            1202 => Self::Expr_LIKE_Expr,
            1203 => Self::Expr_MINUS_Expr,
            1204 => Self::Expr_NOT_ILIKE_Expr,
            1205 => Self::Expr_NOT_IN_Expr_P_IN,
            1206 => Self::Expr_NOT_LIKE_Expr,
            1207 => Self::Expr_OR_Expr,
            1208 => Self::Expr_PERCENT_Expr,
            1209 => Self::Expr_PLUS_Expr,
            1210 => Self::Expr_SLASH_Expr,
            1211 => Self::Expr_STAR_Expr,
            1212 => Self::Expr_Shape,
            1213 => Self::Expr_UNION_Expr,
            1214 => Self::GLOBAL_NodeName,
            1215 => Self::INTROSPECT_TypeExpr,
            1216 => Self::IfThenElseExpr,
            1217 => Self::LANGBRACKET_FullTypeExpr_RANGBRACKET_Expr_P_TYPECAST,
            1218 => Self::LANGBRACKET_OPTIONAL_FullTypeExpr_RANGBRACKET_Expr_P_TYPECAST,
            1219 => Self::LANGBRACKET_REQUIRED_FullTypeExpr_RANGBRACKET_Expr_P_TYPECAST,
            1220 => Self::MINUS_Expr_P_UMINUS,
            1221 => Self::NOT_Expr,
            1222 => Self::PLUS_Expr_P_UMINUS,
            1223 => Self::Path,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ExprList {
    fn from_id(id: usize) -> Self {
        match id {
            1224 => Self::ExprListInner,
            1225 => Self::ExprListInner_COMMA,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ExprListInner {
    fn from_id(id: usize) -> Self {
        match id {
            1226 => Self::ExprListInner_COMMA_GenExpr,
            1227 => Self::GenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ExprStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1228 => Self::ExprStmtAnnoying,
            1229 => Self::ExprStmtSimple,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ExprStmtAnnoying {
    fn from_id(id: usize) -> Self {
        match id {
            1230 => Self::ExprStmtAnnoyingCore,
            1231 => Self::WithBlock_ExprStmtAnnoyingCore,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ExprStmtAnnoyingCore {
    fn from_id(id: usize) -> Self {
        match id {
            1232 => Self::AnnoyingFor,
            1233 => Self::SimpleGroup,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ExprStmtSimple {
    fn from_id(id: usize) -> Self {
        match id {
            1234 => Self::ExprStmtSimpleCore,
            1235 => Self::WithBlock_ExprStmtSimpleCore,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ExprStmtSimpleCore {
    fn from_id(id: usize) -> Self {
        match id {
            1236 => Self::InternalGroup,
            1237 => Self::SimpleDelete,
            1238 => Self::SimpleFor,
            1239 => Self::SimpleInsert,
            1240 => Self::SimpleSelect,
            1241 => Self::SimpleUpdate,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::Extending {
    fn from_id(id: usize) -> Self {
        match id {
            1242 => Self::EXTENDING_TypeNameList,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ExtendingSimple {
    fn from_id(id: usize) -> Self {
        match id {
            1243 => Self::EXTENDING_SimpleTypeNameList,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ExtensionPackageStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1244 => Self::CreateExtensionPackageMigrationStmt,
            1245 => Self::CreateExtensionPackageStmt,
            1246 => Self::DropExtensionPackageMigrationStmt,
            1247 => Self::DropExtensionPackageStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ExtensionRequirementDeclaration {
    fn from_id(id: usize) -> Self {
        match id {
            1248 => Self::USING_EXTENSION_ShortNodeName_OptExtensionVersion,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ExtensionStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1249 => Self::AlterExtensionStmt,
            1250 => Self::CreateExtensionStmt,
            1251 => Self::DropExtensionStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ExtensionVersion {
    fn from_id(id: usize) -> Self {
        match id {
            1252 => Self::VERSION_BaseStringConstant,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FilterClause {
    fn from_id(id: usize) -> Self {
        match id {
            1253 => Self::FILTER_Expr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FreeComputableShapePointer {
    fn from_id(id: usize) -> Self {
        match id {
            1254 => Self::FreeSimpleShapePointer_ASSIGN_GenExpr,
            1255 => Self::MULTI_FreeSimpleShapePointer_ASSIGN_GenExpr,
            1256 => Self::OPTIONAL_FreeSimpleShapePointer_ASSIGN_GenExpr,
            1257 => Self::OPTIONAL_MULTI_FreeSimpleShapePointer_ASSIGN_GenExpr,
            1258 => Self::OPTIONAL_SINGLE_FreeSimpleShapePointer_ASSIGN_GenExpr,
            1259 => Self::REQUIRED_FreeSimpleShapePointer_ASSIGN_GenExpr,
            1260 => Self::REQUIRED_MULTI_FreeSimpleShapePointer_ASSIGN_GenExpr,
            1261 => Self::REQUIRED_SINGLE_FreeSimpleShapePointer_ASSIGN_GenExpr,
            1262 => Self::SINGLE_FreeSimpleShapePointer_ASSIGN_GenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FreeComputableShapePointerList {
    fn from_id(id: usize) -> Self {
        match id {
            1263 => Self::FreeComputableShapePointerListInner,
            1264 => Self::FreeComputableShapePointerListInner_COMMA,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FreeComputableShapePointerListInner {
    fn from_id(id: usize) -> Self {
        match id {
            1265 => Self::FreeComputableShapePointer,
            1266 => Self::FreeComputableShapePointerListInner_COMMA_FreeComputableShapePointer,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FreeShape {
    fn from_id(id: usize) -> Self {
        match id {
            1267 => Self::LBRACE_FreeComputableShapePointerList_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FreeSimpleShapePointer {
    fn from_id(id: usize) -> Self {
        match id {
            1268 => Self::FreeStepName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FreeStepName {
    fn from_id(id: usize) -> Self {
        match id {
            1269 => Self::DUNDERTYPE,
            1270 => Self::ShortNodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FromFunction {
    fn from_id(id: usize) -> Self {
        match id {
            1271 => Self::USING_Identifier_BaseStringConstant,
            1272 => Self::USING_Identifier_EXPRESSION,
            1273 => Self::USING_Identifier_FUNCTION_BaseStringConstant,
            1274 => Self::USING_ParenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FullTypeExpr {
    fn from_id(id: usize) -> Self {
        match id {
            1275 => Self::FullTypeExpr_AMPER_FullTypeExpr,
            1276 => Self::FullTypeExpr_PIPE_FullTypeExpr,
            1277 => Self::LPAREN_FullTypeExpr_RPAREN,
            1278 => Self::TYPEOF_Expr,
            1279 => Self::TypeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FuncApplication {
    fn from_id(id: usize) -> Self {
        match id {
            1280 => Self::NodeName_LPAREN_OptFuncArgList_RPAREN,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FuncArgList {
    fn from_id(id: usize) -> Self {
        match id {
            1281 => Self::FuncArgListInner,
            1282 => Self::FuncArgListInner_COMMA,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FuncArgListInner {
    fn from_id(id: usize) -> Self {
        match id {
            1283 => Self::FuncArgListInner_COMMA_FuncCallArg,
            1284 => Self::FuncCallArg,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FuncCallArg {
    fn from_id(id: usize) -> Self {
        match id {
            1285 => Self::AnyIdentifier_ASSIGN_ExprStmtSimple,
            1286 => Self::ExprStmtSimple,
            1287 => Self::FuncCallArgExpr_OptFilterClause_OptSortClause,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FuncCallArgExpr {
    fn from_id(id: usize) -> Self {
        match id {
            1288 => Self::AnyIdentifier_ASSIGN_Expr,
            1289 => Self::Expr,
            1290 => Self::PARAMETER_ASSIGN_Expr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FuncDeclArg {
    fn from_id(id: usize) -> Self {
        match id {
            1291 => Self::OptParameterKind_FuncDeclArgName_OptDefault,
            1292 => Self::OptParameterKind_FuncDeclArgName_COLON_OptTypeQualifier_FullTypeExpr_OptDefault,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FuncDeclArgList {
    fn from_id(id: usize) -> Self {
        match id {
            1293 => Self::FuncDeclArgListInner,
            1294 => Self::FuncDeclArgListInner_COMMA,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FuncDeclArgListInner {
    fn from_id(id: usize) -> Self {
        match id {
            1295 => Self::FuncDeclArg,
            1296 => Self::FuncDeclArgListInner_COMMA_FuncDeclArg,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FuncDeclArgName {
    fn from_id(id: usize) -> Self {
        match id {
            1297 => Self::Identifier,
            1298 => Self::PARAMETER,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FuncDeclArgs {
    fn from_id(id: usize) -> Self {
        match id {
            1299 => Self::FuncDeclArgList,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FuncExpr {
    fn from_id(id: usize) -> Self {
        match id {
            1300 => Self::FuncApplication,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FunctionDeclaration {
    fn from_id(id: usize) -> Self {
        match id {
            1301 => Self::FUNCTION_NodeName_CreateFunctionArgs_ARROW_OptTypeQualifier_FunctionType_CreateFunctionSDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FunctionDeclarationShort {
    fn from_id(id: usize) -> Self {
        match id {
            1302 => Self::FUNCTION_NodeName_CreateFunctionArgs_ARROW_OptTypeQualifier_FunctionType_CreateFunctionSingleSDLCommandBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FunctionType {
    fn from_id(id: usize) -> Self {
        match id {
            1303 => Self::FullTypeExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FutureRequirementDeclaration {
    fn from_id(id: usize) -> Self {
        match id {
            1304 => Self::USING_FUTURE_ShortNodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::FutureStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1305 => Self::CreateFutureStmt,
            1306 => Self::DropFutureStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::GenExpr {
    fn from_id(id: usize) -> Self {
        match id {
            1307 => Self::Expr,
            1308 => Self::ExprStmtSimpleCore,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::GlobalDeclaration {
    fn from_id(id: usize) -> Self {
        match id {
            1309 => Self::GLOBAL_NodeName_OptPtrTarget_CreateGlobalSDLCommandsBlock,
            1310 => Self::PtrQuals_GLOBAL_NodeName_OptPtrTarget_CreateGlobalSDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::GlobalDeclarationShort {
    fn from_id(id: usize) -> Self {
        match id {
            1311 => Self::GLOBAL_NodeName_ASSIGN_GenExpr,
            1312 => Self::PtrQuals_GLOBAL_NodeName_ASSIGN_GenExpr,
            1313 => Self::GLOBAL_NodeName_PtrTarget,
            1314 => Self::PtrQuals_GLOBAL_NodeName_PtrTarget,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::GroupingAtom {
    fn from_id(id: usize) -> Self {
        match id {
            1315 => Self::GroupingIdent,
            1316 => Self::LPAREN_GroupingIdentList_RPAREN,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::GroupingAtomList {
    fn from_id(id: usize) -> Self {
        match id {
            1317 => Self::GroupingAtomListInner,
            1318 => Self::GroupingAtomListInner_COMMA,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::GroupingAtomListInner {
    fn from_id(id: usize) -> Self {
        match id {
            1319 => Self::GroupingAtom,
            1320 => Self::GroupingAtomListInner_COMMA_GroupingAtom,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::GroupingElement {
    fn from_id(id: usize) -> Self {
        match id {
            1321 => Self::CUBE_LPAREN_GroupingAtomList_RPAREN,
            1322 => Self::GroupingAtom,
            1323 => Self::LBRACE_GroupingElementList_RBRACE,
            1324 => Self::ROLLUP_LPAREN_GroupingAtomList_RPAREN,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::GroupingElementList {
    fn from_id(id: usize) -> Self {
        match id {
            1325 => Self::GroupingElementListInner,
            1326 => Self::GroupingElementListInner_COMMA,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::GroupingElementListInner {
    fn from_id(id: usize) -> Self {
        match id {
            1327 => Self::GroupingElement,
            1328 => Self::GroupingElementListInner_COMMA_GroupingElement,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::GroupingIdent {
    fn from_id(id: usize) -> Self {
        match id {
            1329 => Self::AT_Identifier,
            1330 => Self::DOT_Identifier,
            1331 => Self::Identifier,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::GroupingIdentList {
    fn from_id(id: usize) -> Self {
        match id {
            1332 => Self::GroupingIdent,
            1333 => Self::GroupingIdentList_COMMA_GroupingIdent,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::Identifier {
    fn from_id(id: usize) -> Self {
        match id {
            1334 => Self::IDENT,
            1335 => Self::UnreservedKeyword,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::IfThenElseExpr {
    fn from_id(id: usize) -> Self {
        match id {
            1336 => Self::IF_Expr_THEN_Expr_ELSE_Expr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::IndexArg {
    fn from_id(id: usize) -> Self {
        match id {
            1337 => Self::AnyIdentifier_ASSIGN_Expr,
            1338 => Self::FuncDeclArgName_OptDefault,
            1339 => Self::FuncDeclArgName_COLON_OptTypeQualifier_FullTypeExpr_OptDefault,
            1340 => Self::ParameterKind_FuncDeclArgName_COLON_OptTypeQualifier_FullTypeExpr_OptDefault,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::IndexArgList {
    fn from_id(id: usize) -> Self {
        match id {
            1341 => Self::IndexArgListInner,
            1342 => Self::IndexArgListInner_COMMA,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::IndexArgListInner {
    fn from_id(id: usize) -> Self {
        match id {
            1343 => Self::IndexArg,
            1344 => Self::IndexArgListInner_COMMA_IndexArg,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::IndexDeclaration {
    fn from_id(id: usize) -> Self {
        match id {
            1345 => Self::ABSTRACT_INDEX_NodeName_OptExtendingSimple_CreateIndexSDLCommandsBlock,
            1346 => Self::ABSTRACT_INDEX_NodeName_IndexExtArgList_OptExtendingSimple_CreateIndexSDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::IndexDeclarationShort {
    fn from_id(id: usize) -> Self {
        match id {
            1347 => Self::ABSTRACT_INDEX_NodeName_OptExtendingSimple,
            1348 => Self::ABSTRACT_INDEX_NodeName_IndexExtArgList_OptExtendingSimple,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::IndexExtArgList {
    fn from_id(id: usize) -> Self {
        match id {
            1349 => Self::LPAREN_OptIndexArgList_RPAREN,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::IndirectionEl {
    fn from_id(id: usize) -> Self {
        match id {
            1350 => Self::LBRACKET_COLON_Expr_RBRACKET,
            1351 => Self::LBRACKET_Expr_COLON_Expr_RBRACKET,
            1352 => Self::LBRACKET_Expr_COLON_RBRACKET,
            1353 => Self::LBRACKET_Expr_RBRACKET,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::InnerDDLStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1354 => Self::AlterAliasStmt,
            1355 => Self::AlterAnnotationStmt,
            1356 => Self::AlterCastStmt,
            1357 => Self::AlterConstraintStmt,
            1358 => Self::AlterFunctionStmt,
            1359 => Self::AlterGlobalStmt,
            1360 => Self::AlterIndexStmt,
            1361 => Self::AlterLinkStmt,
            1362 => Self::AlterModuleStmt,
            1363 => Self::AlterObjectTypeStmt,
            1364 => Self::AlterOperatorStmt,
            1365 => Self::AlterPermissionStmt,
            1366 => Self::AlterPropertyStmt,
            1367 => Self::AlterScalarTypeStmt,
            1368 => Self::CreateAliasStmt,
            1369 => Self::CreateAnnotationStmt,
            1370 => Self::CreateCastStmt,
            1371 => Self::CreateConstraintStmt,
            1372 => Self::CreateFunctionStmt,
            1373 => Self::CreateGlobalStmt,
            1374 => Self::CreateIndexMatchStmt,
            1375 => Self::CreateIndexStmt,
            1376 => Self::CreateLinkStmt,
            1377 => Self::CreateModuleStmt,
            1378 => Self::CreateObjectTypeStmt,
            1379 => Self::CreateOperatorStmt,
            1380 => Self::CreatePermissionStmt,
            1381 => Self::CreatePropertyStmt,
            1382 => Self::CreatePseudoTypeStmt,
            1383 => Self::CreateScalarTypeStmt,
            1384 => Self::DropAliasStmt,
            1385 => Self::DropAnnotationStmt,
            1386 => Self::DropCastStmt,
            1387 => Self::DropConstraintStmt,
            1388 => Self::DropFunctionStmt,
            1389 => Self::DropGlobalStmt,
            1390 => Self::DropIndexMatchStmt,
            1391 => Self::DropIndexStmt,
            1392 => Self::DropLinkStmt,
            1393 => Self::DropModuleStmt,
            1394 => Self::DropObjectTypeStmt,
            1395 => Self::DropOperatorStmt,
            1396 => Self::DropPermissionStmt,
            1397 => Self::DropPropertyStmt,
            1398 => Self::DropScalarTypeStmt,
            1399 => Self::ExtensionStmt,
            1400 => Self::FutureStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::InternalGroup {
    fn from_id(id: usize) -> Self {
        match id {
            1401 => Self::FOR_GROUP_OptionallyAliasedExpr_UsingClause_ByClause_IN_Identifier_OptGroupingAlias_UNION_OptionallyAliasedExpr_OptFilterClause_OptSortClause,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::LimitClause {
    fn from_id(id: usize) -> Self {
        match id {
            1402 => Self::LIMIT_Expr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::LinkDeclaration {
    fn from_id(id: usize) -> Self {
        match id {
            1403 => Self::ABSTRACT_LINK_PtrNodeName_OptExtendingSimple_CreateLinkSDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::LinkDeclarationShort {
    fn from_id(id: usize) -> Self {
        match id {
            1404 => Self::ABSTRACT_LINK_PtrNodeName_OptExtendingSimple,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::MigrationStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1405 => Self::AbortMigrationStmt,
            1406 => Self::AlterCurrentMigrationStmt,
            1407 => Self::AlterMigrationStmt,
            1408 => Self::CommitMigrationStmt,
            1409 => Self::CreateMigrationStmt,
            1410 => Self::DropMigrationStmt,
            1411 => Self::PopulateMigrationStmt,
            1412 => Self::ResetSchemaStmt,
            1413 => Self::StartMigrationStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ModuleDeclaration {
    fn from_id(id: usize) -> Self {
        match id {
            1414 => Self::MODULE_ModuleName_SDLCommandBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ModuleName {
    fn from_id(id: usize) -> Self {
        match id {
            1415 => Self::DotName,
            1416 => Self::ModuleName_DOUBLECOLON_DotName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::NamedTuple {
    fn from_id(id: usize) -> Self {
        match id {
            1417 => Self::LPAREN_NamedTupleElementList_RPAREN,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::NamedTupleElement {
    fn from_id(id: usize) -> Self {
        match id {
            1418 => Self::ShortNodeName_ASSIGN_GenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::NamedTupleElementList {
    fn from_id(id: usize) -> Self {
        match id {
            1419 => Self::NamedTupleElementListInner,
            1420 => Self::NamedTupleElementListInner_COMMA,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::NamedTupleElementListInner {
    fn from_id(id: usize) -> Self {
        match id {
            1421 => Self::NamedTupleElement,
            1422 => Self::NamedTupleElementListInner_COMMA_NamedTupleElement,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::NestedQLBlockStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1423 => Self::OptWithDDLStmt,
            1424 => Self::SetFieldStmt,
            1425 => Self::Stmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::NodeName {
    fn from_id(id: usize) -> Self {
        match id {
            1426 => Self::BaseName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::NontrivialTypeExpr {
    fn from_id(id: usize) -> Self {
        match id {
            1428 => Self::LPAREN_FullTypeExpr_RPAREN,
            1429 => Self::TYPEOF_Expr,
            1430 => Self::TypeExpr_AMPER_TypeExpr,
            1431 => Self::TypeExpr_PIPE_TypeExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ObjectTypeDeclaration {
    fn from_id(id: usize) -> Self {
        match id {
            1432 => Self::ABSTRACT_TYPE_NodeName_OptExtendingSimple_CreateObjectTypeSDLCommandsBlock,
            1433 => Self::TYPE_NodeName_OptExtendingSimple_CreateObjectTypeSDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ObjectTypeDeclarationShort {
    fn from_id(id: usize) -> Self {
        match id {
            1434 => Self::ABSTRACT_TYPE_NodeName_OptExtendingSimple,
            1435 => Self::TYPE_NodeName_OptExtendingSimple,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OffsetClause {
    fn from_id(id: usize) -> Self {
        match id {
            1436 => Self::OFFSET_Expr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OnExpr {
    fn from_id(id: usize) -> Self {
        match id {
            1437 => Self::ON_ParenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OnSourceDeleteResetStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1438 => Self::RESET_ON_SOURCE_DELETE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OnSourceDeleteStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1439 => Self::ON_SOURCE_DELETE_ALLOW,
            1440 => Self::ON_SOURCE_DELETE_DELETE_TARGET,
            1441 => Self::ON_SOURCE_DELETE_DELETE_TARGET_IF_ORPHAN,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OnTargetDeleteResetStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1442 => Self::RESET_ON_TARGET_DELETE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OnTargetDeleteStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1443 => Self::ON_TARGET_DELETE_ALLOW,
            1444 => Self::ON_TARGET_DELETE_DEFERRED_RESTRICT,
            1445 => Self::ON_TARGET_DELETE_DELETE_SOURCE,
            1446 => Self::ON_TARGET_DELETE_RESTRICT,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OperatorCode {
    fn from_id(id: usize) -> Self {
        match id {
            1447 => Self::USING_Identifier_BaseStringConstant,
            1448 => Self::USING_Identifier_EXPRESSION,
            1449 => Self::USING_Identifier_FUNCTION_BaseStringConstant,
            1450 => Self::USING_Identifier_OPERATOR_BaseStringConstant,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OperatorKind {
    fn from_id(id: usize) -> Self {
        match id {
            1451 => Self::INFIX,
            1452 => Self::POSTFIX,
            1453 => Self::PREFIX,
            1454 => Self::TERNARY,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptAlterUsingClause {
    fn from_id(id: usize) -> Self {
        match id {
            1455 => Self::USING_ParenExpr,
            1456 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptAnySubShape {
    fn from_id(id: usize) -> Self {
        match id {
            1457 => Self::COLON_Shape,
            1458 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptConcreteConstraintArgList {
    fn from_id(id: usize) -> Self {
        match id {
            1459 => Self::LPAREN_OptPosCallArgList_RPAREN,
            1460 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateAccessPolicyCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1461 => Self::CreateAccessPolicyCommandsBlock,
            1462 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateAnnotationCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1463 => Self::CreateAnnotationCommandsBlock,
            1464 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1465 => Self::CreateCommandsBlock,
            1466 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateConcreteLinkCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1467 => Self::CreateConcreteLinkCommandsBlock,
            1468 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateConcretePropertyCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1469 => Self::CreateConcretePropertyCommandsBlock,
            1470 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateDatabaseCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1471 => Self::CreateDatabaseCommandsBlock,
            1472 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateExtensionCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1473 => Self::CreateExtensionCommandsBlock,
            1474 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateExtensionPackageCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1475 => Self::CreateExtensionPackageCommandsBlock,
            1476 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateGlobalCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1477 => Self::CreateGlobalCommandsBlock,
            1478 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateIndexCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1479 => Self::CreateIndexCommandsBlock,
            1480 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateIndexMatchCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1481 => Self::CreateIndexMatchCommandsBlock,
            1482 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateLinkCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1483 => Self::CreateLinkCommandsBlock,
            1484 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateMigrationCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1485 => Self::CreateMigrationCommandsBlock,
            1486 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateObjectTypeCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1487 => Self::CreateObjectTypeCommandsBlock,
            1488 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateOperatorCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1489 => Self::CreateOperatorCommandsBlock,
            1490 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreatePermissionCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1491 => Self::CreatePermissionCommandsBlock,
            1492 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreatePropertyCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1493 => Self::CreatePropertyCommandsBlock,
            1494 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreatePseudoTypeCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1495 => Self::CreatePseudoTypeCommandsBlock,
            1496 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateRewriteCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1497 => Self::CreateRewriteCommandsBlock,
            1498 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateRoleCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1499 => Self::CreateRoleCommandsBlock,
            1500 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateScalarTypeCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1501 => Self::CreateScalarTypeCommandsBlock,
            1502 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptCreateTriggerCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1503 => Self::CreateTriggerCommandsBlock,
            1504 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptDefault {
    fn from_id(id: usize) -> Self {
        match id {
            1505 => Self::EQUALS_Expr,
            1506 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptDeferred {
    fn from_id(id: usize) -> Self {
        match id {
            1507 => Self::DEFERRED,
            1508 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptDelegated {
    fn from_id(id: usize) -> Self {
        match id {
            1509 => Self::DELEGATED,
            1510 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptDirection {
    fn from_id(id: usize) -> Self {
        match id {
            1511 => Self::ASC,
            1512 => Self::DESC,
            1513 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptDropConcreteIndexCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1514 => Self::DropConcreteIndexCommandsBlock,
            1515 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptDropConcreteLinkCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1516 => Self::DropConcreteLinkCommandsBlock,
            1517 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptDropLinkCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1518 => Self::DropLinkCommandsBlock,
            1519 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptDropObjectTypeCommandsBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1520 => Self::DropObjectTypeCommandsBlock,
            1521 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptExceptExpr {
    fn from_id(id: usize) -> Self {
        match id {
            1522 => Self::EXCEPT_ParenExpr,
            1523 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptExprList {
    fn from_id(id: usize) -> Self {
        match id {
            1524 => Self::ExprList,
            1525 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptExtending {
    fn from_id(id: usize) -> Self {
        match id {
            1526 => Self::Extending,
            1527 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptExtendingSimple {
    fn from_id(id: usize) -> Self {
        match id {
            1528 => Self::ExtendingSimple,
            1529 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptExtensionVersion {
    fn from_id(id: usize) -> Self {
        match id {
            1530 => Self::ExtensionVersion,
            1531 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptFilterClause {
    fn from_id(id: usize) -> Self {
        match id {
            1532 => Self::FilterClause,
            1533 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptFuncArgList {
    fn from_id(id: usize) -> Self {
        match id {
            1534 => Self::FuncArgList,
            1535 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptGroupingAlias {
    fn from_id(id: usize) -> Self {
        match id {
            1536 => Self::COMMA_Identifier,
            1537 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptIfNotExists {
    fn from_id(id: usize) -> Self {
        match id {
            1538 => Self::IF_NOT_EXISTS,
            1539 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptIndexArgList {
    fn from_id(id: usize) -> Self {
        match id {
            1540 => Self::IndexArgList,
            1541 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptIndexExtArgList {
    fn from_id(id: usize) -> Self {
        match id {
            1542 => Self::IndexExtArgList,
            1543 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptMigrationNameParentName {
    fn from_id(id: usize) -> Self {
        match id {
            1544 => Self::ShortNodeName,
            1545 => Self::ShortNodeName_ONTO_ShortNodeName,
            1546 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptNonesOrder {
    fn from_id(id: usize) -> Self {
        match id {
            1547 => Self::EMPTY_FIRST,
            1548 => Self::EMPTY_LAST,
            1549 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptOnExpr {
    fn from_id(id: usize) -> Self {
        match id {
            1550 => Self::OnExpr,
            1551 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptParameterKind {
    fn from_id(id: usize) -> Self {
        match id {
            1552 => Self::ParameterKind,
            1553 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptPosCallArgList {
    fn from_id(id: usize) -> Self {
        match id {
            1554 => Self::PosCallArgList,
            1555 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptPosition {
    fn from_id(id: usize) -> Self {
        match id {
            1556 => Self::AFTER_NodeName,
            1557 => Self::BEFORE_NodeName,
            1558 => Self::FIRST,
            1559 => Self::LAST,
            1560 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptPtrQuals {
    fn from_id(id: usize) -> Self {
        match id {
            1561 => Self::PtrQuals,
            1562 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptPtrTarget {
    fn from_id(id: usize) -> Self {
        match id {
            1563 => Self::PtrTarget,
            1564 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptSelectLimit {
    fn from_id(id: usize) -> Self {
        match id {
            1565 => Self::SelectLimit,
            1566 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptSemicolons {
    fn from_id(id: usize) -> Self {
        match id {
            1567 => Self::Semicolons,
            1568 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptShortExtending {
    fn from_id(id: usize) -> Self {
        match id {
            1569 => Self::ShortExtending,
            1570 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptSortClause {
    fn from_id(id: usize) -> Self {
        match id {
            1571 => Self::SortClause,
            1572 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptSuperuser {
    fn from_id(id: usize) -> Self {
        match id {
            1573 => Self::SUPERUSER,
            1574 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptTransactionModeList {
    fn from_id(id: usize) -> Self {
        match id {
            1575 => Self::TransactionModeList,
            1576 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptTypeIntersection {
    fn from_id(id: usize) -> Self {
        match id {
            1577 => Self::TypeIntersection,
            1578 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptTypeQualifier {
    fn from_id(id: usize) -> Self {
        match id {
            1579 => Self::OPTIONAL,
            1580 => Self::SET_OF,
            1581 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptUnlessConflictClause {
    fn from_id(id: usize) -> Self {
        match id {
            1582 => Self::UnlessConflictCause,
            1583 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptUsingBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1584 => Self::USING_ParenExpr,
            1585 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptUsingClause {
    fn from_id(id: usize) -> Self {
        match id {
            1586 => Self::UsingClause,
            1587 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptWhenBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1588 => Self::WHEN_ParenExpr,
            1589 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptWithDDLStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1590 => Self::DDLWithBlock_WithDDLStmt,
            1591 => Self::WithDDLStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptionalOptional {
    fn from_id(id: usize) -> Self {
        match id {
            1592 => Self::OPTIONAL,
            1593 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OptionallyAliasedExpr {
    fn from_id(id: usize) -> Self {
        match id {
            1594 => Self::AliasedExpr,
            1595 => Self::Expr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OrderbyExpr {
    fn from_id(id: usize) -> Self {
        match id {
            1596 => Self::Expr_OptDirection_OptNonesOrder,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::OrderbyList {
    fn from_id(id: usize) -> Self {
        match id {
            1597 => Self::OrderbyExpr,
            1598 => Self::OrderbyList_THEN_OrderbyExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ParameterKind {
    fn from_id(id: usize) -> Self {
        match id {
            1599 => Self::NAMEDONLY,
            1600 => Self::VARIADIC,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ParenExpr {
    fn from_id(id: usize) -> Self {
        match id {
            1601 => Self::LPAREN_ExprStmt_RPAREN,
            1602 => Self::LPAREN_Expr_RPAREN,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ParenTypeExpr {
    fn from_id(id: usize) -> Self {
        match id {
            1603 => Self::LPAREN_FullTypeExpr_RPAREN,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PartialReservedKeyword {
    fn from_id(id: usize) -> Self {
        match id {
            1604 => Self::EXCEPT,
            1605 => Self::INTERSECT,
            1606 => Self::UNION,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::Path {
    fn from_id(id: usize) -> Self {
        match id {
            1607 => Self::Expr_PathStep_P_DOT,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PathNodeName {
    fn from_id(id: usize) -> Self {
        match id {
            1608 => Self::PtrIdentifier,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PathStep {
    fn from_id(id: usize) -> Self {
        match id {
            1609 => Self::AT_PathNodeName,
            1610 => Self::DOTBW_PathStepName,
            1611 => Self::DOT_ICONST,
            1612 => Self::DOT_PathStepName,
            1613 => Self::TypeIntersection,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PathStepName {
    fn from_id(id: usize) -> Self {
        match id {
            1614 => Self::DUNDERTYPE,
            1615 => Self::PathNodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PermissionDeclaration {
    fn from_id(id: usize) -> Self {
        match id {
            1616 => Self::PERMISSION_NodeName_CreatePermissionSDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PermissionDeclarationShort {
    fn from_id(id: usize) -> Self {
        match id {
            1617 => Self::PERMISSION_NodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PointerName {
    fn from_id(id: usize) -> Self {
        match id {
            1618 => Self::DUNDERTYPE,
            1619 => Self::PtrNodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PopulateMigrationStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1620 => Self::POPULATE_MIGRATION,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PosCallArg {
    fn from_id(id: usize) -> Self {
        match id {
            1621 => Self::Expr_OptFilterClause_OptSortClause,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PosCallArgList {
    fn from_id(id: usize) -> Self {
        match id {
            1622 => Self::PosCallArg,
            1623 => Self::PosCallArgList_COMMA_PosCallArg,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PropertyDeclaration {
    fn from_id(id: usize) -> Self {
        match id {
            1624 => Self::ABSTRACT_PROPERTY_PtrNodeName_OptExtendingSimple_CreatePropertySDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PropertyDeclarationShort {
    fn from_id(id: usize) -> Self {
        match id {
            1625 => Self::ABSTRACT_PROPERTY_PtrNodeName_OptExtendingSimple,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PtrIdentifier {
    fn from_id(id: usize) -> Self {
        match id {
            1626 => Self::Identifier,
            1627 => Self::PartialReservedKeyword,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PtrName {
    fn from_id(id: usize) -> Self {
        match id {
            1628 => Self::PtrIdentifier,
            1629 => Self::QualifiedName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PtrNodeName {
    fn from_id(id: usize) -> Self {
        match id {
            1630 => Self::PtrName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PtrQualifiedNodeName {
    fn from_id(id: usize) -> Self {
        match id {
            1631 => Self::QualifiedName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PtrQuals {
    fn from_id(id: usize) -> Self {
        match id {
            1632 => Self::MULTI,
            1633 => Self::OPTIONAL,
            1634 => Self::OPTIONAL_MULTI,
            1635 => Self::OPTIONAL_SINGLE,
            1636 => Self::REQUIRED,
            1637 => Self::REQUIRED_MULTI,
            1638 => Self::REQUIRED_SINGLE,
            1639 => Self::SINGLE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::PtrTarget {
    fn from_id(id: usize) -> Self {
        match id {
            1640 => Self::ARROW_FullTypeExpr,
            1641 => Self::COLON_FullTypeExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::QualifiedName {
    fn from_id(id: usize) -> Self {
        match id {
            1642 => Self::DUNDERSTD_DOUBLECOLON_ColonedIdents,
            1643 => Self::Identifier_DOUBLECOLON_ColonedIdents,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::RenameStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1644 => Self::RENAME_TO_NodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ReservedKeyword {
    fn from_id(id: usize) -> Self {
        match id {
            1645 => Self::ADMINISTER,
            1646 => Self::ALTER,
            1647 => Self::ANALYZE,
            1648 => Self::AND,
            1649 => Self::ANYARRAY,
            1650 => Self::ANYOBJECT,
            1651 => Self::ANYTUPLE,
            1652 => Self::ANYTYPE,
            1653 => Self::BEGIN,
            1654 => Self::BY,
            1655 => Self::CASE,
            1656 => Self::CHECK,
            1657 => Self::COMMIT,
            1658 => Self::CONFIGURE,
            1659 => Self::CREATE,
            1660 => Self::DEALLOCATE,
            1661 => Self::DELETE,
            1662 => Self::DESCRIBE,
            1663 => Self::DETACHED,
            1664 => Self::DISCARD,
            1665 => Self::DISTINCT,
            1666 => Self::DO,
            1667 => Self::DROP,
            1668 => Self::DUNDERDEFAULT,
            1669 => Self::DUNDEREDGEDBSYS,
            1670 => Self::DUNDEREDGEDBTPL,
            1671 => Self::DUNDERNEW,
            1672 => Self::DUNDEROLD,
            1673 => Self::DUNDERSOURCE,
            1674 => Self::DUNDERSPECIFIED,
            1675 => Self::DUNDERSTD,
            1676 => Self::DUNDERSUBJECT,
            1677 => Self::DUNDERTYPE,
            1678 => Self::ELSE,
            1679 => Self::END,
            1680 => Self::EXISTS,
            1681 => Self::EXPLAIN,
            1682 => Self::EXTENDING,
            1683 => Self::FALSE,
            1684 => Self::FETCH,
            1685 => Self::FILTER,
            1686 => Self::FOR,
            1687 => Self::GET,
            1688 => Self::GLOBAL,
            1689 => Self::GRANT,
            1690 => Self::GROUP,
            1691 => Self::IF,
            1692 => Self::ILIKE,
            1693 => Self::IMPORT,
            1694 => Self::IN,
            1695 => Self::INSERT,
            1696 => Self::INTROSPECT,
            1697 => Self::IS,
            1698 => Self::LIKE,
            1699 => Self::LIMIT,
            1700 => Self::LISTEN,
            1701 => Self::LOAD,
            1702 => Self::LOCK,
            1703 => Self::MATCH,
            1704 => Self::MODULE,
            1705 => Self::MOVE,
            1706 => Self::NEVER,
            1707 => Self::NOT,
            1708 => Self::NOTIFY,
            1709 => Self::OFFSET,
            1710 => Self::ON,
            1711 => Self::OPTIONAL,
            1712 => Self::OR,
            1713 => Self::OVER,
            1714 => Self::PARTITION,
            1715 => Self::PREPARE,
            1716 => Self::RAISE,
            1717 => Self::REFRESH,
            1718 => Self::REVOKE,
            1719 => Self::ROLLBACK,
            1720 => Self::SELECT,
            1721 => Self::SET,
            1722 => Self::SINGLE,
            1723 => Self::START,
            1724 => Self::TRUE,
            1725 => Self::TYPEOF,
            1726 => Self::UPDATE,
            1727 => Self::VARIADIC,
            1728 => Self::WHEN,
            1729 => Self::WINDOW,
            1730 => Self::WITH,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ResetFieldStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1731 => Self::RESET_DEFAULT,
            1732 => Self::RESET_IDENT,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ResetSchemaStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1733 => Self::RESET_SCHEMA_TO_NodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ResetStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1734 => Self::RESET_ALIAS_Identifier,
            1735 => Self::RESET_ALIAS_STAR,
            1736 => Self::RESET_MODULE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::RewriteDeclarationBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1737 => Self::REWRITE_RewriteKindList_USING_ParenExpr_CreateRewriteSDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::RewriteDeclarationShort {
    fn from_id(id: usize) -> Self {
        match id {
            1738 => Self::REWRITE_RewriteKindList_USING_ParenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::RewriteKind {
    fn from_id(id: usize) -> Self {
        match id {
            1739 => Self::INSERT,
            1740 => Self::UPDATE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::RewriteKindList {
    fn from_id(id: usize) -> Self {
        match id {
            1741 => Self::RewriteKind,
            1742 => Self::RewriteKindList_COMMA_RewriteKind,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::RoleStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1743 => Self::AlterRoleStmt,
            1744 => Self::CreateRoleStmt,
            1745 => Self::DropRoleStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SDLBlockStatement {
    fn from_id(id: usize) -> Self {
        match id {
            1746 => Self::AliasDeclaration,
            1747 => Self::AnnotationDeclaration,
            1748 => Self::ConstraintDeclaration,
            1749 => Self::FunctionDeclaration,
            1750 => Self::GlobalDeclaration,
            1751 => Self::IndexDeclaration,
            1752 => Self::LinkDeclaration,
            1753 => Self::ModuleDeclaration,
            1754 => Self::ObjectTypeDeclaration,
            1755 => Self::PermissionDeclaration,
            1756 => Self::PropertyDeclaration,
            1757 => Self::ScalarTypeDeclaration,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SDLCommandBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1758 => Self::LBRACE_OptSemicolons_RBRACE,
            1759 => Self::LBRACE_OptSemicolons_SDLStatements_RBRACE,
            1760 => Self::LBRACE_OptSemicolons_SDLShortStatement_RBRACE,
            1761 => Self::LBRACE_OptSemicolons_SDLStatements_OptSemicolons_SDLShortStatement_RBRACE,
            1762 => Self::LBRACE_OptSemicolons_SDLStatements_Semicolons_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SDLDocument {
    fn from_id(id: usize) -> Self {
        match id {
            1763 => Self::OptSemicolons,
            1764 => Self::OptSemicolons_SDLStatements,
            1765 => Self::OptSemicolons_SDLStatements_Semicolons,
            1766 => Self::OptSemicolons_SDLShortStatement,
            1767 => Self::OptSemicolons_SDLStatements_OptSemicolons_SDLShortStatement,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SDLShortStatement {
    fn from_id(id: usize) -> Self {
        match id {
            1768 => Self::AliasDeclarationShort,
            1769 => Self::AnnotationDeclarationShort,
            1770 => Self::ConstraintDeclarationShort,
            1771 => Self::ExtensionRequirementDeclaration,
            1772 => Self::FunctionDeclarationShort,
            1773 => Self::FutureRequirementDeclaration,
            1774 => Self::GlobalDeclarationShort,
            1775 => Self::IndexDeclarationShort,
            1776 => Self::LinkDeclarationShort,
            1777 => Self::ObjectTypeDeclarationShort,
            1778 => Self::PermissionDeclarationShort,
            1779 => Self::PropertyDeclarationShort,
            1780 => Self::ScalarTypeDeclarationShort,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SDLStatement {
    fn from_id(id: usize) -> Self {
        match id {
            1781 => Self::SDLBlockStatement,
            1782 => Self::SDLShortStatement_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SDLStatements {
    fn from_id(id: usize) -> Self {
        match id {
            1783 => Self::SDLStatement,
            1784 => Self::SDLStatements_OptSemicolons_SDLStatement,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ScalarTypeDeclaration {
    fn from_id(id: usize) -> Self {
        match id {
            1785 => Self::ABSTRACT_SCALAR_TYPE_NodeName_OptExtending_CreateScalarTypeSDLCommandsBlock,
            1786 => Self::SCALAR_TYPE_NodeName_OptExtending_CreateScalarTypeSDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ScalarTypeDeclarationShort {
    fn from_id(id: usize) -> Self {
        match id {
            1787 => Self::ABSTRACT_SCALAR_TYPE_NodeName_OptExtending,
            1788 => Self::SCALAR_TYPE_NodeName_OptExtending,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SchemaItem {
    fn from_id(id: usize) -> Self {
        match id {
            1789 => Self::SchemaObjectClass_NodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SchemaObjectClass {
    fn from_id(id: usize) -> Self {
        match id {
            1790 => Self::ALIAS,
            1791 => Self::ANNOTATION,
            1792 => Self::CAST,
            1793 => Self::CONSTRAINT,
            1794 => Self::FUNCTION,
            1795 => Self::LINK,
            1796 => Self::MODULE,
            1797 => Self::OPERATOR,
            1798 => Self::PROPERTY,
            1799 => Self::SCALAR_TYPE,
            1800 => Self::TYPE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SelectLimit {
    fn from_id(id: usize) -> Self {
        match id {
            1801 => Self::LimitClause,
            1802 => Self::OffsetClause,
            1803 => Self::OffsetClause_LimitClause,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::Semicolons {
    fn from_id(id: usize) -> Self {
        match id {
            1804 => Self::SEMICOLON,
            1805 => Self::Semicolons_SEMICOLON,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SessionStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1806 => Self::ResetStmt,
            1807 => Self::SetStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::Set {
    fn from_id(id: usize) -> Self {
        match id {
            1808 => Self::LBRACE_OptExprList_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SetAnnotation {
    fn from_id(id: usize) -> Self {
        match id {
            1809 => Self::ANNOTATION_NodeName_ASSIGN_GenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SetCardinalityStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1810 => Self::RESET_CARDINALITY_OptAlterUsingClause,
            1811 => Self::SET_MULTI,
            1812 => Self::SET_SINGLE_OptAlterUsingClause,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SetDelegatedStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1813 => Self::RESET_DELEGATED,
            1814 => Self::SET_DELEGATED,
            1815 => Self::SET_NOT_DELEGATED,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SetField {
    fn from_id(id: usize) -> Self {
        match id {
            1816 => Self::Identifier_ASSIGN_GenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SetFieldStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1817 => Self::SET_Identifier_ASSIGN_GenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SetGlobalTypeStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1818 => Self::RESET_TYPE,
            1819 => Self::SETTYPE_FullTypeExpr_OptAlterUsingClause,
            1820 => Self::SETTYPE_FullTypeExpr_RESET_TO_DEFAULT,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SetPointerTypeStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1821 => Self::RESET_TYPE,
            1822 => Self::SETTYPE_FullTypeExpr_OptAlterUsingClause,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SetRequiredInCreateStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1823 => Self::SET_REQUIRED_OptAlterUsingClause,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SetRequiredStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1824 => Self::DROP_REQUIRED,
            1825 => Self::RESET_OPTIONALITY,
            1826 => Self::SET_OPTIONAL,
            1827 => Self::SET_REQUIRED_OptAlterUsingClause,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SetStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1828 => Self::SET_ALIAS_Identifier_AS_MODULE_ModuleName,
            1829 => Self::SET_MODULE_ModuleName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::Shape {
    fn from_id(id: usize) -> Self {
        match id {
            1830 => Self::LBRACE_RBRACE,
            1831 => Self::LBRACE_ShapeElementList_RBRACE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ShapeElement {
    fn from_id(id: usize) -> Self {
        match id {
            1832 => Self::ComputableShapePointer,
            1833 => Self::ShapePointer_OptAnySubShape_OptFilterClause_OptSortClause_OptSelectLimit,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ShapeElementList {
    fn from_id(id: usize) -> Self {
        match id {
            1834 => Self::ShapeElementListInner,
            1835 => Self::ShapeElementListInner_COMMA,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ShapeElementListInner {
    fn from_id(id: usize) -> Self {
        match id {
            1836 => Self::ShapeElement,
            1837 => Self::ShapeElementListInner_COMMA_ShapeElement,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ShapePath {
    fn from_id(id: usize) -> Self {
        match id {
            1838 => Self::AT_PathNodeName,
            1839 => Self::PathStepName_OptTypeIntersection,
            1840 => Self::Splat,
            1841 => Self::TypeIntersection_DOT_PathStepName_OptTypeIntersection,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ShapePointer {
    fn from_id(id: usize) -> Self {
        match id {
            1842 => Self::ShapePath,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ShortExtending {
    fn from_id(id: usize) -> Self {
        match id {
            1843 => Self::EXTENDING_ShortTypeNameList,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ShortNodeName {
    fn from_id(id: usize) -> Self {
        match id {
            1844 => Self::Identifier,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ShortTypeName {
    fn from_id(id: usize) -> Self {
        match id {
            1845 => Self::ShortNodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::ShortTypeNameList {
    fn from_id(id: usize) -> Self {
        match id {
            1846 => Self::ShortTypeName,
            1847 => Self::ShortTypeNameList_COMMA_ShortTypeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SimpleDelete {
    fn from_id(id: usize) -> Self {
        match id {
            1848 => Self::DELETE_Expr_OptFilterClause_OptSortClause_OptSelectLimit,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SimpleFor {
    fn from_id(id: usize) -> Self {
        match id {
            1849 => Self::FOR_OptionalOptional_Identifier_IN_AtomicExpr_UNION_Expr,
            1850 => Self::FOR_OptionalOptional_Identifier_IN_AtomicExpr_ExprStmtSimple,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SimpleGroup {
    fn from_id(id: usize) -> Self {
        match id {
            1851 => Self::GROUP_OptionallyAliasedExpr_OptUsingClause_ByClause,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SimpleInsert {
    fn from_id(id: usize) -> Self {
        match id {
            1852 => Self::INSERT_Expr_OptUnlessConflictClause,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SimpleSelect {
    fn from_id(id: usize) -> Self {
        match id {
            1853 => Self::SELECT_OptionallyAliasedExpr_OptFilterClause_OptSortClause_OptSelectLimit,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SimpleShapePath {
    fn from_id(id: usize) -> Self {
        match id {
            1854 => Self::AT_PathNodeName,
            1855 => Self::PathStepName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SimpleShapePointer {
    fn from_id(id: usize) -> Self {
        match id {
            1856 => Self::SimpleShapePath,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SimpleTypeName {
    fn from_id(id: usize) -> Self {
        match id {
            1857 => Self::ANYOBJECT,
            1858 => Self::ANYTUPLE,
            1859 => Self::ANYTYPE,
            1860 => Self::PtrNodeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SimpleTypeNameList {
    fn from_id(id: usize) -> Self {
        match id {
            1861 => Self::SimpleTypeName,
            1862 => Self::SimpleTypeNameList_COMMA_SimpleTypeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SimpleUpdate {
    fn from_id(id: usize) -> Self {
        match id {
            1863 => Self::UPDATE_Expr_OptFilterClause_SET_Shape,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SingleStatement {
    fn from_id(id: usize) -> Self {
        match id {
            1864 => Self::ConfigStmt,
            1865 => Self::DDLStmt,
            1866 => Self::IfThenElseExpr,
            1867 => Self::SessionStmt,
            1868 => Self::Stmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SortClause {
    fn from_id(id: usize) -> Self {
        match id {
            1869 => Self::ORDERBY_OrderbyList,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::Splat {
    fn from_id(id: usize) -> Self {
        match id {
            1870 => Self::DOUBLESTAR,
            1871 => Self::ParenTypeExpr_DOT_DOUBLESTAR,
            1872 => Self::ParenTypeExpr_DOT_STAR,
            1873 => Self::ParenTypeExpr_TypeIntersection_DOT_DOUBLESTAR,
            1874 => Self::ParenTypeExpr_TypeIntersection_DOT_STAR,
            1875 => Self::PathStepName_DOT_DOUBLESTAR,
            1876 => Self::PathStepName_DOT_STAR,
            1877 => Self::PathStepName_TypeIntersection_DOT_DOUBLESTAR,
            1878 => Self::PathStepName_TypeIntersection_DOT_STAR,
            1879 => Self::PtrQualifiedNodeName_DOT_DOUBLESTAR,
            1880 => Self::PtrQualifiedNodeName_DOT_STAR,
            1881 => Self::PtrQualifiedNodeName_TypeIntersection_DOT_DOUBLESTAR,
            1882 => Self::PtrQualifiedNodeName_TypeIntersection_DOT_STAR,
            1883 => Self::STAR,
            1884 => Self::TypeIntersection_DOT_DOUBLESTAR,
            1885 => Self::TypeIntersection_DOT_STAR,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::StartMigrationStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1886 => Self::START_MIGRATION_TO_SDLCommandBlock,
            1887 => Self::START_MIGRATION_REWRITE,
            1888 => Self::START_MIGRATION_TO_COMMITTED_SCHEMA,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::StatementBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1889 => Self::SingleStatement,
            1890 => Self::StatementBlock_Semicolons_SingleStatement,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::Stmt {
    fn from_id(id: usize) -> Self {
        match id {
            1891 => Self::AdministerStmt,
            1892 => Self::AnalyzeStmt,
            1893 => Self::DescribeStmt,
            1894 => Self::ExprStmt,
            1895 => Self::TransactionStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::StringInterpolation {
    fn from_id(id: usize) -> Self {
        match id {
            1896 => Self::STRINTERPSTART_StringInterpolationTail,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::StringInterpolationTail {
    fn from_id(id: usize) -> Self {
        match id {
            1897 => Self::Expr_STRINTERPCONT_StringInterpolationTail,
            1898 => Self::Expr_STRINTERPEND,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::Subtype {
    fn from_id(id: usize) -> Self {
        match id {
            1899 => Self::BaseNumberConstant,
            1900 => Self::BaseStringConstant,
            1901 => Self::FullTypeExpr,
            1902 => Self::Identifier_COLON_FullTypeExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SubtypeList {
    fn from_id(id: usize) -> Self {
        match id {
            1903 => Self::SubtypeListInner,
            1904 => Self::SubtypeListInner_COMMA,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::SubtypeListInner {
    fn from_id(id: usize) -> Self {
        match id {
            1905 => Self::Subtype,
            1906 => Self::SubtypeListInner_COMMA_Subtype,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::TransactionMode {
    fn from_id(id: usize) -> Self {
        match id {
            1907 => Self::DEFERRABLE,
            1908 => Self::ISOLATION_REPEATABLE_READ,
            1909 => Self::ISOLATION_SERIALIZABLE,
            1910 => Self::NOT_DEFERRABLE,
            1911 => Self::READ_ONLY,
            1912 => Self::READ_WRITE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::TransactionModeList {
    fn from_id(id: usize) -> Self {
        match id {
            1913 => Self::TransactionMode,
            1914 => Self::TransactionModeList_COMMA_TransactionMode,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::TransactionStmt {
    fn from_id(id: usize) -> Self {
        match id {
            1915 => Self::COMMIT,
            1916 => Self::DECLARE_SAVEPOINT_Identifier,
            1917 => Self::RELEASE_SAVEPOINT_Identifier,
            1918 => Self::ROLLBACK,
            1919 => Self::ROLLBACK_TO_SAVEPOINT_Identifier,
            1920 => Self::START_TRANSACTION_OptTransactionModeList,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::TriggerDeclarationBlock {
    fn from_id(id: usize) -> Self {
        match id {
            1921 => Self::TRIGGER_NodeName_TriggerTiming_TriggerKindList_FOR_TriggerScope_OptWhenBlock_DO_ParenExpr_CreateTriggerSDLCommandsBlock,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::TriggerDeclarationShort {
    fn from_id(id: usize) -> Self {
        match id {
            1922 => Self::TRIGGER_NodeName_TriggerTiming_TriggerKindList_FOR_TriggerScope_OptWhenBlock_DO_ParenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::TriggerKind {
    fn from_id(id: usize) -> Self {
        match id {
            1923 => Self::DELETE,
            1924 => Self::INSERT,
            1925 => Self::UPDATE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::TriggerKindList {
    fn from_id(id: usize) -> Self {
        match id {
            1926 => Self::TriggerKind,
            1927 => Self::TriggerKindList_COMMA_TriggerKind,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::TriggerScope {
    fn from_id(id: usize) -> Self {
        match id {
            1928 => Self::ALL,
            1929 => Self::EACH,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::TriggerTiming {
    fn from_id(id: usize) -> Self {
        match id {
            1930 => Self::AFTER,
            1931 => Self::AFTER_COMMIT_OF,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::Tuple {
    fn from_id(id: usize) -> Self {
        match id {
            1932 => Self::LPAREN_GenExpr_COMMA_OptExprList_RPAREN,
            1933 => Self::LPAREN_RPAREN,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::TypeExpr {
    fn from_id(id: usize) -> Self {
        match id {
            1934 => Self::NontrivialTypeExpr,
            1935 => Self::SimpleTypeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::TypeIntersection {
    fn from_id(id: usize) -> Self {
        match id {
            1936 => Self::LBRACKET_IS_FullTypeExpr_RBRACKET,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::TypeName {
    fn from_id(id: usize) -> Self {
        match id {
            1937 => Self::CollectionTypeName,
            1938 => Self::SimpleTypeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::TypeNameList {
    fn from_id(id: usize) -> Self {
        match id {
            1939 => Self::TypeName,
            1940 => Self::TypeNameList_COMMA_TypeName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::UnlessConflictCause {
    fn from_id(id: usize) -> Self {
        match id {
            1941 => Self::UNLESS_CONFLICT_UnlessConflictSpecifier,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::UnlessConflictSpecifier {
    fn from_id(id: usize) -> Self {
        match id {
            1942 => Self::ON_Expr,
            1943 => Self::ON_Expr_ELSE_Expr,
            1944 => Self::epsilon,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::UnqualifiedPointerName {
    fn from_id(id: usize) -> Self {
        match id {
            1945 => Self::PointerName,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::UnreservedKeyword {
    fn from_id(id: usize) -> Self {
        match id {
            1946 => Self::ABORT,
            1947 => Self::ABSTRACT,
            1948 => Self::ACCESS,
            1949 => Self::AFTER,
            1950 => Self::ALIAS,
            1951 => Self::ALL,
            1952 => Self::ALLOW,
            1953 => Self::ANNOTATION,
            1954 => Self::APPLIED,
            1955 => Self::AS,
            1956 => Self::ASC,
            1957 => Self::ASSIGNMENT,
            1958 => Self::BEFORE,
            1959 => Self::BLOBAL,
            1960 => Self::BRANCH,
            1961 => Self::CARDINALITY,
            1962 => Self::CAST,
            1963 => Self::COMMITTED,
            1964 => Self::CONFIG,
            1965 => Self::CONFLICT,
            1966 => Self::CONSTRAINT,
            1967 => Self::CUBE,
            1968 => Self::CURRENT,
            1969 => Self::DATA,
            1970 => Self::DATABASE,
            1971 => Self::DDL,
            1972 => Self::DECLARE,
            1973 => Self::DEFAULT,
            1974 => Self::DEFERRABLE,
            1975 => Self::DEFERRED,
            1976 => Self::DELEGATED,
            1977 => Self::DENY,
            1978 => Self::DESC,
            1979 => Self::EACH,
            1980 => Self::EMPTY,
            1981 => Self::EXPRESSION,
            1982 => Self::EXTENSION,
            1983 => Self::FINAL,
            1984 => Self::FIRST,
            1985 => Self::FORCE,
            1986 => Self::FROM,
            1987 => Self::FUNCTION,
            1988 => Self::FUTURE,
            1989 => Self::IMPLICIT,
            1990 => Self::INDEX,
            1991 => Self::INFIX,
            1992 => Self::INHERITABLE,
            1993 => Self::INSTANCE,
            1994 => Self::INTO,
            1995 => Self::ISOLATION,
            1996 => Self::JSON,
            1997 => Self::LAST,
            1998 => Self::LINK,
            1999 => Self::MIGRATION,
            2000 => Self::MULTI,
            2001 => Self::NAMED,
            2002 => Self::OBJECT,
            2003 => Self::OF,
            2004 => Self::ONLY,
            2005 => Self::ONTO,
            2006 => Self::OPERATOR,
            2007 => Self::OPTIONALITY,
            2008 => Self::ORDER,
            2009 => Self::ORPHAN,
            2010 => Self::OVERLOADED,
            2011 => Self::OWNED,
            2012 => Self::PACKAGE,
            2013 => Self::PERMISSION,
            2014 => Self::POLICY,
            2015 => Self::POPULATE,
            2016 => Self::POSTFIX,
            2017 => Self::PREFIX,
            2018 => Self::PROPERTY,
            2019 => Self::PROPOSED,
            2020 => Self::PSEUDO,
            2021 => Self::READ,
            2022 => Self::REJECT,
            2023 => Self::RELEASE,
            2024 => Self::RENAME,
            2025 => Self::REPEATABLE,
            2026 => Self::REQUIRED,
            2027 => Self::RESET,
            2028 => Self::RESTRICT,
            2029 => Self::REWRITE,
            2030 => Self::ROLE,
            2031 => Self::ROLES,
            2032 => Self::ROLLUP,
            2033 => Self::SAVEPOINT,
            2034 => Self::SCALAR,
            2035 => Self::SCHEMA,
            2036 => Self::SDL,
            2037 => Self::SERIALIZABLE,
            2038 => Self::SESSION,
            2039 => Self::SOURCE,
            2040 => Self::SUPERUSER,
            2041 => Self::SYSTEM,
            2042 => Self::TARGET,
            2043 => Self::TEMPLATE,
            2044 => Self::TERNARY,
            2045 => Self::TEXT,
            2046 => Self::THEN,
            2047 => Self::TO,
            2048 => Self::TRANSACTION,
            2049 => Self::TRIGGER,
            2050 => Self::TYPE,
            2051 => Self::UNLESS,
            2052 => Self::USING,
            2053 => Self::VERBOSE,
            2054 => Self::VERSION,
            2055 => Self::VIEW,
            2056 => Self::WRITE,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::Using {
    fn from_id(id: usize) -> Self {
        match id {
            2057 => Self::USING_ParenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::UsingClause {
    fn from_id(id: usize) -> Self {
        match id {
            2058 => Self::USING_AliasedExprList,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::UsingStmt {
    fn from_id(id: usize) -> Self {
        match id {
            2059 => Self::RESET_EXPRESSION,
            2060 => Self::USING_ParenExpr,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::WithBlock {
    fn from_id(id: usize) -> Self {
        match id {
            2061 => Self::WITH_WithDeclList,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::WithDDLStmt {
    fn from_id(id: usize) -> Self {
        match id {
            2062 => Self::InnerDDLStmt,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::WithDecl {
    fn from_id(id: usize) -> Self {
        match id {
            2063 => Self::AliasDecl,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::WithDeclList {
    fn from_id(id: usize) -> Self {
        match id {
            2064 => Self::WithDeclListInner,
            2065 => Self::WithDeclListInner_COMMA,
            _ => unreachable!("reduction {id}"),
        }
    }
}

impl super::FromId for super::WithDeclListInner {
    fn from_id(id: usize) -> Self {
        match id {
            2066 => Self::WithDecl,
            2067 => Self::WithDeclListInner_COMMA_WithDecl,
            _ => unreachable!("reduction {id}"),
        }
    }
}
