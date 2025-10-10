use std::collections::HashMap;
use std::str::FromStr;

use gel_schema::{
    Class, ContainerTy, EnumTy, Expression, ObjectListTy, Value, Version, VersionStage,
};
use pyo3::exceptions::PyAssertionError;
use pyo3::types::{
    PyBool, PyDict, PyFloat, PyFrozenSet, PyInt, PyList, PySet, PyString, PyTuple, PyType,
};
use pyo3::{IntoPyObjectExt, PyTypeInfo};
use pyo3::{conversion::FromPyObjectBound, prelude::*};
use uuid::Uuid;

#[pymodule]
pub fn _schema(_py: Python, m: &Bound<PyModule>) -> PyResult<()> {
    m.add_class::<Schema>()?;
    Ok(())
}

#[pyclass(frozen, module = "edb.schema._schema")]
#[derive(Clone, Default)]
struct Schema {
    inner: gel_schema::Schema,
}

#[pymethods]
impl Schema {
    #[staticmethod]
    pub fn empty() -> Self {
        Schema {
            inner: gel_schema::Schema::default(),
        }
    }

    #[staticmethod]
    pub fn parse_reflection(base_schema: &Schema, reflected_json: &str) -> Self {
        let layouts = gel_schema::get_structures();

        let schema = gel_schema::parse_reflection(&base_schema.inner, reflected_json, &layouts);
        Schema { inner: schema }
    }

    #[pyo3(signature = (pretty=false))]
    pub fn dump(&self, pretty: bool) -> String {
        if pretty {
            format!("{:#?}", self.inner)
        } else {
            format!("{:?}", self.inner)
        }
    }

    #[staticmethod]
    fn decode(encoded: &[u8]) -> PyResult<Schema> {
        let inner =
            bincode::deserialize(encoded).map_err(|x| SchemaError::new_err(x.to_string()))?;
        Ok(Schema { inner })
    }

    fn __reduce__<'p>(self_: Bound<'p, Self>, py: Python<'p>) -> PyResult<Bound<'p, PyAny>> {
        let decode_fn = self_.get_type().getattr("decode")?;

        let encoded = bincode::serialize(&self_.get().inner)
            .map_err(|x| SchemaError::new_err(x.to_string()))?;

        (decode_fn, (encoded,)).into_bound_py_any(py)
    }

    pub fn has_object(&self, id: Uuid) -> bool {
        self.inner.has_object(&id)
    }

    pub fn get_by_id<'p>(&self, py: Python<'p>, id: Uuid) -> PyResult<Option<Bound<'p, PyAny>>> {
        let Some(obj) = self.inner.get_by_id(id) else {
            return Ok(None);
        };
        object_into_py(py, &obj).map(Some)
    }

    pub fn get_by_name<'p>(
        &self,
        py: Python<'p>,
        name: Bound<'p, PyAny>,
    ) -> PyResult<Option<Bound<'p, PyAny>>> {
        let name = name_from_py(name)?;
        if name.module.is_none() {
            return Ok(None);
        }

        let Some(obj) = self.inner.get_by_name(&name) else {
            return Ok(None);
        };
        object_into_py(py, &obj).map(Some)
    }

    pub fn get_by_global_name<'p>(
        &self,
        py: Python<'p>,
        cls: Bound<PyType>,
        name: Bound<'p, PyAny>,
    ) -> PyResult<Option<Bound<'p, PyAny>>> {
        let cls = cls_from_py(cls).unwrap();
        let name = name_from_py(name)?;

        let Some(obj) = self.inner.get_by_global_name(cls, name) else {
            return Ok(None);
        };
        object_into_py(py, &obj).map(Some)
    }

    pub fn get_by_short_name<'p>(
        &self,
        py: Python<'p>,
        cls: Bound<PyType>,
        name: Bound<'p, PyAny>,
    ) -> PyResult<Bound<'p, PyAny>> {
        let cls = cls_from_py(cls).unwrap();
        let name = name_from_py(name)?;

        let results_rs = self.inner.get_by_short_name(cls, name);

        let mut results_py = Vec::new();
        for obj in results_rs {
            results_py.push(object_into_py(py, &obj)?);
        }
        if results_py.is_empty() {
            py.None().into_bound_py_any(py)
        } else {
            Ok(PyTuple::new(py, results_py)?.into_any())
        }
    }

    pub fn get_obj_data_raw<'p>(
        &self,
        py: Python<'p>,
        obj: Bound<'p, PyAny>,
    ) -> PyResult<Option<Bound<'p, PyTuple>>> {
        let obj = object_from_py(obj)?;

        let Some(data) = self.inner.get_obj_data_raw(&obj) else {
            return Ok(None);
        };

        let mut data_py = Vec::with_capacity(data.len());
        for value in data {
            data_py.push(value_into_py(py, value)?);
        }
        PyTuple::new(py, data_py).map(Some)
    }

    pub fn get_obj_field_raw<'p>(
        &self,
        py: Python<'p>,
        obj: Bound<'p, PyAny>,
        field_index: usize,
    ) -> PyResult<Option<Bound<'p, PyAny>>> {
        let obj = object_from_py(obj)?;

        let Some(data) = self.inner.get_obj_data_raw(&obj) else {
            return Err(PyAssertionError::new_err(format!(
                "cannot get data: schema object {obj:?} does not exist in this schema"
            )));
        };

        let Some(value) = data.get(field_index) else {
            return Ok(None);
        };
        value_into_py(py, value).map(Some)
    }

    pub fn _get_object_ids<'p>(&self, py: Python<'p>) -> PyResult<Bound<'p, PyList>> {
        PyList::new(py, self.inner.get_object_ids())
    }

    pub fn _get_global_name_ids<'p>(&self, py: Python<'p>) -> PyResult<Bound<'p, PyList>> {
        PyList::new(
            py,
            (self.inner.get_global_name_ids()).map(|(cls, id)| (cls_into_py(py, cls), id)),
        )
    }

    pub fn add_raw<'p>(
        &self,
        py: Python<'p>,
        id: Uuid,
        mcls: Bound<'p, PyType>,
        data: Bound<'p, PyTuple>,
    ) -> PyResult<Self> {
        let cls = cls_from_py(mcls)?;
        let obj = gel_schema::Object::new(cls, id);

        let mut data_vec = Vec::with_capacity(data.len());
        for value in data {
            data_vec.push(value_from_py(py, value)?)
        }

        let mut inner = self.inner.clone();
        inner
            .add_raw(&obj, data_vec)
            .map_err(SchemaError::new_err)?;
        Ok(Schema { inner })
    }

    pub fn delete<'p>(&self, obj: Bound<'p, PyAny>) -> PyResult<Schema> {
        let obj = object_from_py(obj)?;

        let mut inner = self.inner.clone();
        inner.delete(&obj).map_err(SchemaError::new_err)?;
        Ok(Schema { inner })
    }

    pub fn delist<'p>(&self, name: Bound<'p, PyAny>) -> PyResult<Schema> {
        let name = name_from_py(name)?;

        let mut inner = self.inner.clone();
        inner.delist(&name);
        Ok(Schema { inner })
    }

    pub fn set_obj_field<'p>(
        &self,
        py: Python<'p>,
        obj: Bound<PyAny>,
        fieldname: &str,
        value: Bound<PyAny>,
    ) -> PyResult<Schema> {
        let obj = object_from_py(obj)?;
        let value = value_from_py(py, value)?;

        let mut inner = self.inner.clone();
        inner
            .set_obj_field(obj, fieldname, value)
            .map_err(SchemaError::new_err)?;
        Ok(Schema { inner })
    }

    pub fn unset_obj_field<'p>(&self, obj: Bound<PyAny>, fieldname: &str) -> PyResult<Schema> {
        let obj = object_from_py(obj)?;

        let mut inner = self.inner.clone();
        inner
            .unset_obj_field(obj, fieldname)
            .map_err(SchemaError::new_err)?;
        Ok(Schema { inner })
    }

    pub fn update_obj<'p>(
        &self,
        py: Python<'p>,
        obj: Bound<PyAny>,
        updates: Bound<PyDict>,
    ) -> PyResult<Schema> {
        if updates.is_empty() {
            return Ok(self.clone());
        }

        let obj = object_from_py(obj)?;

        let mut updates_rs = HashMap::with_capacity(updates.len());
        for (fieldname, value) in updates {
            let fieldname: String = fieldname.extract()?;
            let value = value_from_py(py, value)?;
            updates_rs.insert(fieldname, value);
        }

        let mut inner = self.inner.clone();
        inner
            .update_obj(obj, updates_rs)
            .map_err(SchemaError::new_err)?;
        Ok(Schema { inner })
    }

    pub fn get_referrers<'p>(
        &self,
        py: Python<'p>,
        obj: Bound<PyAny>,
        referrer_class: Option<Bound<'p, PyType>>,
        referrer_field: Option<&str>,
    ) -> PyResult<Bound<'p, PyFrozenSet>> {
        // from py
        let obj = object_from_py(obj)?;
        let cls = referrer_class.map(cls_from_py).transpose()?;

        // inner
        let referrers = self.inner.get_referrers(obj, cls, referrer_field);

        // to py
        object_set_into_py(py, referrers.iter())
    }

    pub fn get_referrers_ex<'p>(
        &self,
        py: Python<'p>,
        obj: Bound<PyAny>,
        referrer_class: Option<Bound<'p, PyType>>,
    ) -> PyResult<Bound<'p, PyDict>> {
        // from py
        let obj = object_from_py(obj)?;
        let referrer_class = referrer_class.map(cls_from_py).transpose()?;

        // inner
        let referrers = self.inner.get_referrers_ex(obj, referrer_class);

        // into py
        let res = PyDict::new(py);
        for ((cls, f), r) in referrers {
            let cls = cls_into_py(py, cls);
            res.set_item((cls, f), object_set_into_py(py, r.iter())?)?;
        }
        Ok(res)
    }
}

fn cls_from_py(ty: Bound<PyType>) -> PyResult<gel_schema::Class> {
    let ty_name = ty.name()?;
    let ty_name: &str = ty_name.extract()?;
    gel_schema::Class::from_str(ty_name)
        .map_err(|_| SchemaError::new_err(format!("Unknown schema class {ty_name}")))
}

fn cls_into_py<'p>(py: Python<'p>, cls: Class) -> Bound<'p, PyAny> {
    let get_schema_class = imports::get_schema_class(py).unwrap();
    get_schema_class.call1((cls.as_ref(),)).unwrap()
}

fn name_from_py(name: Bound<PyAny>) -> PyResult<gel_schema::Name> {
    let name: Bound<PyTuple> = name.cast_into()?;

    let first = name.get_item(0)?;
    let first = String::from_py_object_bound(first.as_borrowed())?;

    Ok(if let Some(second) = name.get_item(1).ok() {
        let second = String::from_py_object_bound(second.as_borrowed())?;
        gel_schema::Name {
            module: Some(first),
            object: second,
        }
    } else {
        gel_schema::Name {
            module: None,
            object: first,
        }
    })
}

fn name_into_py<'p>(py: Python<'p>, name: &gel_schema::Name) -> PyResult<Bound<'p, PyAny>> {
    if let Some(module) = &name.module {
        let name_cls = imports::QualName(py)?;

        let args = PyDict::new(py);
        args.set_item("module", module)?;
        args.set_item("name", &name.object)?;
        name_cls.call((), Some(&args))
    } else {
        let name_cls = imports::UnqualName(py)?;
        name_cls.call((&name.object,), None)
    }
}

fn object_into_py<'p>(py: Python<'p>, obj: &gel_schema::Object) -> PyResult<Bound<'p, PyAny>> {
    let cls_name: &str = obj.class().as_ref();

    let object_cls = imports::Object(py)?;
    let raw_schema_restore = object_cls.getattr("raw_schema_restore")?;

    raw_schema_restore.call((cls_name, obj.id()), Default::default())
}

fn object_from_py(obj: Bound<'_, PyAny>) -> PyResult<gel_schema::Object> {
    let id: uuid::Uuid = obj.getattr("id")?.extract()?;

    let cls = cls_from_py(obj.get_type())?;
    Ok(gel_schema::Object::new(cls, id))
}

fn object_set_into_py<'p, 'a>(
    py: Python<'p>,
    objects: impl Iterator<Item = &'a gel_schema::Object>,
) -> PyResult<Bound<'p, PyFrozenSet>> {
    PyFrozenSet::new(
        py,
        objects
            .map(|o| object_into_py(py, o))
            .collect::<PyResult<Vec<_>>>()?,
    )
}

fn value_into_py<'p>(py: Python<'p>, val: &gel_schema::Value) -> PyResult<Bound<'p, PyAny>> {
    match val {
        gel_schema::Value::Object(obj) => {
            let cls_name: &str = obj.class().as_ref();

            (cls_name, obj.id()).into_bound_py_any(py)
        }

        gel_schema::Value::ObjectDict {
            keys,
            values,
            value_ty,
        } => {
            let value_cls = ty_to_py(py, value_ty)?;

            (
                "ObjectDict",
                (PyString::type_object(py), value_cls),
                PyTuple::new(py, values)?,
                (("_keys", PyTuple::new(py, keys)?),),
            )
                .into_bound_py_any(py)
        }

        gel_schema::Value::ObjectList {
            ty,
            values,
            value_ty,
        } => {
            let value_cls = value_ty.as_ref().map(|v| ty_ref_to_py(py, v)).transpose()?;
            let value_cls = value_cls.unwrap_or_else(|| py.None().bind(py).clone());

            (ty.as_ref(), value_cls, PyTuple::new(py, values)?, ()).into_bound_py_any(py)
        }

        gel_schema::Value::ObjectSet { values, value_ty } => {
            let value_cls = value_ty.as_ref().map(|t| ty_to_py(py, t)).transpose()?;

            ("ObjectSet", value_cls, PyTuple::new(py, values)?, ()).into_bound_py_any(py)
        }

        gel_schema::Value::ObjectIndex {
            ty,
            value_ty,
            values,
            keys,
        } => {
            let value_cls = ty_to_py(py, value_ty)?;

            let keys = if let Some(keys) = keys {
                let keys: Vec<_> = keys
                    .iter()
                    .map(|n| name_into_py(py, n))
                    .collect::<PyResult<_>>()?;
                PyTuple::new(py, keys)?.into_bound_py_any(py)?
            } else {
                py.None().into_bound_py_any(py)?
            };

            (
                ty.as_ref(),
                value_cls,
                PyTuple::new(py, values)?,
                (("_keys", keys),),
            )
                .into_bound_py_any(py)
        }

        gel_schema::Value::Name(name) => name_into_py(py, name),

        gel_schema::Value::Expression(expression) => expr_into_py(py, expression),

        gel_schema::Value::ExpressionList(exprs) => {
            let expr_cls = imports::Expression(py)?;
            let list_cls = imports::ExpressionList(py)?;

            let mut values_py = Vec::new();
            for expr in exprs {
                let expr_data = expr_into_py(py, expr)?;
                let expr = expr_cls.call_method("schema_restore", (expr_data,), None)?;
                values_py.push(expr);
            }
            list_cls.call1((values_py,))
        }
        gel_schema::Value::ExpressionDict(_btree_map) => todo!(),

        gel_schema::Value::Uuid(v) => v.into_bound_py_any(py),
        gel_schema::Value::Bool(v) => v.into_bound_py_any(py),
        gel_schema::Value::Int(v) => v.into_bound_py_any(py),
        gel_schema::Value::Float(v) => v.into_bound_py_any(py),
        gel_schema::Value::Str(v) => v.into_bound_py_any(py),
        gel_schema::Value::Container {
            ty,
            value_ty,
            values,
        } => {
            let cls = match *ty {
                ContainerTy::FrozenCheckedList => imports::FrozenCheckedList(py)?,
                ContainerTy::FrozenCheckedSet => imports::FrozenCheckedSet(py)?,
                ContainerTy::ExpressionList => imports::ExpressionList(py)?,
                ContainerTy::CheckedList => imports::CheckedList(py)?,
                ContainerTy::MultiPropSet => imports::MultiPropSet(py)?,
            };

            // parametrize
            let value_ty = ty_to_py(py, &value_ty)?;
            let cls = cls.call_method("__class_getitem__", (value_ty,), None)?;

            let mut values_py = Vec::new();
            for item in values {
                values_py.push(value_into_py(py, item)?);
            }
            cls.call1((values_py,))
        }
        gel_schema::Value::Enum(enum_ty, variant_name) => {
            let enum_cls = match *enum_ty {
                EnumTy::Language => imports::Language(py)?,
                EnumTy::ExprType => imports::ExprType(py)?,
                EnumTy::SchemaCardinality => imports::SchemaCardinality(py)?,
                EnumTy::LinkTargetDeleteAction => imports::LinkTargetDeleteAction(py)?,
                EnumTy::LinkSourceDeleteAction => imports::LinkSourceDeleteAction(py)?,
                EnumTy::OperatorKind => imports::OperatorKind(py)?,
                EnumTy::Volatility => imports::Volatility(py)?,
                EnumTy::ParameterKind => imports::ParameterKind(py)?,
                EnumTy::TypeModifier => imports::TypeModifier(py)?,
                EnumTy::AccessPolicyAction => imports::AccessPolicyAction(py)?,
                EnumTy::AccessKind => imports::AccessKind(py)?,
                EnumTy::TriggerTiming => imports::TriggerTiming(py)?,
                EnumTy::TriggerKind => imports::TriggerKind(py)?,
                EnumTy::TriggerScope => imports::TriggerScope(py)?,
                EnumTy::RewriteKind => imports::RewriteKind(py)?,
                EnumTy::MigrationGeneratedBy => imports::MigrationGeneratedBy(py)?,
                EnumTy::IndexDeferrability => imports::IndexDeferrability(py)?,
                EnumTy::SplatStrategy => imports::SplatStrategy(py)?,
            };
            enum_cls.getattr(variant_name)
        }
        gel_schema::Value::Version(version) => {
            let cls = imports::Version(py)?;

            let stage_cls = imports::VersionStage(py)?;
            let stage = stage_cls.getattr(version.stage.as_ref())?;

            cls.call(
                (
                    version.major,
                    version.minor,
                    stage,
                    version.stage_no,
                    PyTuple::new(py, &version.local)?,
                ),
                None,
            )
        }

        gel_schema::Value::None => Ok(py.None().bind(py).clone()),
    }
}

fn expr_into_py<'p>(py: Python<'p>, expression: &Expression) -> PyResult<Bound<'p, PyAny>> {
    (
        &expression.text,
        (
            "ObjectSet",
            None::<&str>,
            PyTuple::new(py, &expression.refs)?,
            (),
        ),
        &expression.origin,
    )
        .into_bound_py_any(py)
}

fn value_from_py<'p>(py: Python<'p>, val: Bound<'p, PyAny>) -> PyResult<Value> {
    if val.is_none() {
        return Ok(Value::None);
    }

    if let Ok(val) = val.cast_exact::<PyBool>() {
        return Ok(Value::Bool(val.is_true()));
    }
    if let Ok(val) = val.cast_exact::<PyInt>() {
        return Ok(Value::Int(val.extract()?));
    }
    if let Ok(val) = val.cast_exact::<PyFloat>() {
        return Ok(Value::Float(val.extract()?));
    }
    if let Ok(val) = val.cast_exact::<PyString>() {
        return Ok(Value::Str(val.to_string()));
    }
    if let Ok(uuid) = val.extract() {
        return Ok(Value::Uuid(uuid));
    }

    if let Ok(val) = val.cast_exact::<PyTuple>() {
        let ty_name = val.get_item(0)?;
        let ty_name = ty_name.cast_exact::<PyString>()?.to_str()?;

        if ty_name == "ObjectList" {
            return Ok(Value::ObjectList {
                ty: ObjectListTy::ObjectList,
                value_ty: ty_name_from_py(val.get_item(1)?)?,
                values: uuids_from_py(val.get_item(2)?)?,
            });
        }
        if ty_name == "FuncParameterList" {
            return Ok(Value::ObjectList {
                ty: ObjectListTy::FuncParameterList,
                value_ty: ty_name_from_py(val.get_item(1)?)?,
                values: uuids_from_py(val.get_item(2)?)?,
            });
        }
        if ty_name == "ObjectSet" {
            return Ok(Value::ObjectSet {
                value_ty: ty_name_from_py(val.get_item(1)?)?,
                values: uuids_from_py(val.get_item(2)?)?,
            });
        }
        if ty_name == "ObjectDict" {
            let ty_args = val.get_item(1)?;

            // let key_ty = ty_args.get_item(0)?.to_string();
            let value_ty = ty_name_from_py(ty_args.get_item(1)?)?.unwrap();

            let values = uuids_from_py(val.get_item(2)?)?;

            let attrs = val.get_item(3)?;
            let keys = attrs.get_item(0)?.get_item(1)?;
            let keys = keys
                .cast_into_exact::<PyTuple>()?
                .iter()
                .map(|x| x.to_string())
                .collect();
            return Ok(Value::ObjectDict {
                keys,
                values,
                value_ty,
            });
        }

        const OBJECT_INDEXES: &[&str] = &[
            "ObjectIndexByShortname",
            "ObjectIndexByFullname",
            "ObjectIndexByUnqualifiedName",
            "ObjectIndexByConstraintName",
        ];
        if OBJECT_INDEXES.contains(&ty_name) {
            let ty = Value::get_object_index_ty_name(ty_name);

            let ty_arg = val.get_item(1)?;
            let value_ty = ty_arg.getattr("__name__")?.to_string();

            let values = uuids_from_py(val.get_item(2)?)?;

            let attrs = val.get_item(3)?;
            let keys = attrs.get_item(0)?.get_item(1)?;
            let keys = if keys.is_none() {
                None
            } else {
                let keys = keys.cast_into_exact::<PyTuple>()?;
                Some(
                    keys.iter()
                        .map(|x| name_from_py(x))
                        .collect::<PyResult<Vec<_>>>()?,
                )
            };

            return Ok(Value::ObjectIndex {
                ty,
                value_ty,
                values,
                keys,
            });
        }

        // Expression: this is dodgy matching, we should remove schema_reduce
        if val.len() == 3 {
            let text = val.get_item(0)?;
            let refs = val.get_item(1)?;
            let origin = val.get_item(2)?;

            if let (Ok(text), Ok(refs)) =
                (text.cast_exact::<PyString>(), refs.cast_exact::<PyTuple>())
            {
                let refs = refs.get_item(2)?.cast_into_exact::<PyTuple>()?;
                let refs: Vec<uuid::Uuid> =
                    refs.iter().map(|r| r.extract()).collect::<PyResult<_>>()?;

                return Ok(Value::Expression(Expression {
                    text: text.to_string(),
                    refs,
                    origin: if origin.is_none() {
                        None
                    } else {
                        Some(origin.to_string())
                    },
                }));
            }
        }

        if let Ok(class) = gel_schema::Class::from_str(ty_name) {
            let id = val.get_item(1)?.extract()?;
            return Ok(Value::Object(gel_schema::Object::new(class, id)));
        }
    }

    // weird: this shouldn't be necessary, because nothing is reduced as a list
    // nevertheless Object.bases, is sometimes reduced to a list of uuids
    if let Ok(val) = val.cast_exact::<PyList>() {
        return Ok(Value::ObjectList {
            ty: ObjectListTy::ObjectList,
            value_ty: Some("InheritingObject".into()),
            values: val
                .iter()
                .map(|v| v.extract())
                .collect::<PyResult<Vec<Uuid>>>()?,
        });
    }

    let name = imports::Name(py)?;
    if val.is_instance(&name)? {
        return Ok(Value::Name(name_from_py(val)?));
    }

    let span = imports::Span(py)?;
    if val.is_instance(&span)? {
        return Ok(Value::None);
    }

    let expr_list = imports::ExpressionList(py)?;
    if val.is_instance(&expr_list)? {
        // values
        let list = val.getattr("_container")?.cast_into_exact::<PyList>()?;

        let mut exprs = Vec::with_capacity(list.len());
        for item in list {
            let Value::Expression(expr) = value_from_py(py, item)? else {
                panic!()
            };
            exprs.push(expr);
        }
        return Ok(Value::ExpressionList(exprs));
    }

    let checked_list = imports::AbstractCheckedList(py)?;
    if val.is_instance(&checked_list)? {
        let ty_name = val.get_type().getattr("__name__")?.to_string();
        let ty_name = ty_name.split_once('[').map(|(n, _)| n).unwrap_or(&ty_name);
        let ty = Value::get_container_ty_name(ty_name);

        let value_ty = val.getattr("type")?.getattr("__name__")?.to_string();

        // values
        let list = val.getattr("_container")?.cast_into_exact::<PyList>()?;
        let mut values = Vec::with_capacity(list.len());
        for item in list {
            values.push(value_from_py(py, item)?);
        }

        return Ok(Value::Container {
            ty,
            values,
            value_ty,
        });
    }

    let checked_set = imports::FrozenCheckedSet(py)?;
    if val.is_instance(&checked_set)? {
        let value_ty = val.getattr("type")?.getattr("__name__")?.to_string();

        // values
        let set = val.getattr("_container")?.cast_into_exact::<PySet>()?;
        let mut values = Vec::with_capacity(set.len());
        for item in set {
            values.push(value_from_py(py, item)?);
        }

        return Ok(Value::Container {
            ty: gel_schema::ContainerTy::FrozenCheckedSet,
            values,
            value_ty,
        });
    }

    let str_enum = imports::StrEnum(py)?;
    if val.is_instance(&str_enum)? {
        let bound = val.get_type().name()?;
        let enum_name = bound.to_str()?;
        let variant_name = val.to_string();
        let val = Value::parse_enum(enum_name, &variant_name)
            .unwrap_or_else(|| panic!("Unknown enum variant: {enum_name}.{variant_name}",));
        return Ok(val);
    }
    let int_enum = imports::IntEnum(py)?;
    if val.is_instance(&int_enum)? {
        let ty_name = val.get_type().name()?;
        let enum_name = ty_name.to_str()?;

        let val = val.getattr("_name_")?.cast_into_exact::<PyString>()?;

        let val = Value::parse_enum(enum_name, val.to_str()?)
            .unwrap_or_else(|| panic!("Unknown enum variant: {enum_name}.{val}",));
        return Ok(val);
    }

    let expr_cls = imports::Expression(py)?;
    if val.is_instance(expr_cls)? {
        let text = val.getattr("text")?.to_string();
        let refs_object_set = val.getattr("refs")?;
        let refs = if refs_object_set.is_none() {
            Vec::new()
        } else {
            uuids_from_py(refs_object_set.call_method0("ids")?)?
        };
        let origin = opt_str_from_py(val.getattr("origin")?)?;
        return Ok(Value::Expression(Expression { text, refs, origin }));
    }

    let version_cls = imports::Version(py)?;
    if val.is_instance(version_cls)? {
        let stage = val.getattr("stage")?.getattr("_name_")?.to_string();
        let local: Vec<String> = val.getattr("local")?.extract()?;

        return Ok(Value::Version(Version {
            major: val.getattr("major")?.extract()?,
            minor: val.getattr("minor")?.extract()?,
            stage: VersionStage::from_str(&stage).unwrap(),
            stage_no: val.getattr("stage_no")?.extract()?,
            local,
        }));
    }

    let msg = format!("value_from_py: {val:#?}");
    Err(pyo3::exceptions::PyNotImplementedError::new_err(msg))
}

fn uuids_from_py(val: Bound<'_, PyAny>) -> Result<Vec<Uuid>, PyErr> {
    Ok(val
        .cast_into_exact::<PyTuple>()?
        .iter()
        .map(|v| v.extract())
        .collect::<PyResult<Vec<Uuid>>>()?)
}

fn opt_str_from_py(val: Bound<PyAny>) -> PyResult<Option<String>> {
    if val.is_none() {
        Ok(None)
    } else {
        Ok(Some(val.to_string()))
    }
}

fn ty_name_from_py(val: Bound<'_, PyAny>) -> Result<Option<String>, PyErr> {
    if val.is_none() {
        Ok(None)
    } else if let Ok(val_str) = val.cast_exact::<PyString>() {
        Ok(Some(val_str.to_string()))
    } else {
        // it must be an instance of type, invoke __name__
        let name = val.getattr("__name__")?;
        Ok(Some(name.to_string()))
    }
}

fn ty_ref_to_py<'p>(py: Python<'p>, reference: &str) -> PyResult<Bound<'p, PyAny>> {
    if !reference.contains('.') {
        reference.trim_matches('\'').into_bound_py_any(py)
    } else {
        import_fq(py, reference)
    }
}

fn ty_to_py<'p>(py: Python<'p>, reference: &str) -> PyResult<Bound<'p, PyAny>> {
    if !reference.contains('.') {
        let ty_name = reference.trim_matches('\'');
        match ty_name {
            "int" => Ok(PyInt::type_object(py).into_any()),
            "str" => Ok(PyString::type_object(py).into_any()),
            "Object" => imports::Object(py).cloned(),
            "Type" => imports::Type(py).cloned(),
            "AnnotationValue" => imports::AnnotationValue(py).cloned(),
            "Pointer" => imports::Pointer(py).cloned(),
            "Constraint" => imports::Constraint(py).cloned(),
            "AccessKind" => imports::AccessKind(py).cloned(),
            "AccessPolicy" => imports::AccessPolicy(py).cloned(),
            "Global" => imports::Global(py).cloned(),
            "Permission" => imports::Permission(py).cloned(),
            "ObjectType" => imports::ObjectType(py).cloned(),
            "Extension" => imports::Extension(py).cloned(),
            "Index" => imports::Index(py).cloned(),
            "Migration" => imports::Migration(py).cloned(),
            "Expression" => imports::Expression(py).cloned(),
            "Version" => imports::Version(py).cloned(),
            _ => panic!("todo import of type: {ty_name}"),
        }
    } else {
        import_fq(py, reference)
    }
}

fn import_fq<'p>(py: Python<'p>, fq: &str) -> PyResult<Bound<'p, PyAny>> {
    assert!(!fq.contains('<'));
    let (module, cls) = fq
        .rsplit_once('.')
        .unwrap_or_else(|| panic!("cannot import {fq}"));
    let module = py.import(module)?;
    module.getattr(cls)
}

pyo3::import_exception!(edb.errors, SchemaError);

mod imports {
    #![allow(non_snake_case)]

    use pyo3::prelude::*;
    use pyo3::sync::PyOnceLock;

    pub fn Object(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.objects", "Object")
    }

    pub fn get_schema_class(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.get_or_try_init(py, || {
            let s_obj = py.import("edb.schema.objects")?;
            let obj_meta_cls = s_obj.getattr("ObjectMeta")?;
            let method = obj_meta_cls.getattr("get_schema_class")?;
            Ok(method.unbind())
        })
        .map(|o| o.bind(py))
    }
    pub fn MultiPropSet(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.objects", "MultiPropSet")
    }
    pub fn Type(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.types", "Type")
    }
    pub fn AnnotationValue(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.annos", "AnnotationValue")
    }
    pub fn Pointer(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.pointers", "Pointer")
    }
    pub fn Constraint(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.constraints", "Constraint")
    }
    pub fn AccessPolicy(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.policies", "AccessPolicy")
    }
    pub fn Global(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.globals", "Global")
    }
    pub fn Permission(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.permissions", "Permission")
    }
    pub fn ObjectType(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.objtypes", "ObjectType")
    }
    pub fn Extension(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.extensions", "Extension")
    }
    pub fn Index(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.indexes", "Index")
    }
    pub fn Migration(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.migrations", "Migration")
    }
    pub fn Expression(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.expr", "Expression")
    }
    pub fn ExpressionList(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.expr", "ExpressionList")
    }

    pub fn StrEnum(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.common.enum", "StrEnum")
    }
    pub fn IntEnum(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "enum", "IntEnum")
    }

    pub fn Name(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.name", "Name")
    }
    pub fn QualName(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.name", "QualName")
    }
    pub fn UnqualName(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.name", "UnqualName")
    }

    pub fn Span(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.common.span", "Span")
    }

    pub fn AbstractCheckedList(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.common.checked", "AbstractCheckedList")
    }
    pub fn FrozenCheckedSet(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.common.checked", "FrozenCheckedSet")
    }
    pub fn FrozenCheckedList(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.common.checked", "FrozenCheckedList")
    }
    pub fn CheckedList(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.common.checked", "CheckedList")
    }

    pub fn Version(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.common.verutils", "Version")
    }
    pub fn VersionStage(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.common.verutils", "VersionStage")
    }

    pub fn Language(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.edgeql.ast", "Language")
    }
    pub fn ExprType(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.schema.types", "ExprType")
    }

    pub fn SchemaCardinality(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.edgeql.qltypes", "SchemaCardinality")
    }
    pub fn LinkTargetDeleteAction(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.edgeql.qltypes", "LinkTargetDeleteAction")
    }
    pub fn LinkSourceDeleteAction(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.edgeql.qltypes", "LinkSourceDeleteAction")
    }
    pub fn OperatorKind(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.edgeql.qltypes", "OperatorKind")
    }
    pub fn Volatility(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.edgeql.qltypes", "Volatility")
    }
    pub fn ParameterKind(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.edgeql.qltypes", "ParameterKind")
    }
    pub fn TypeModifier(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.edgeql.qltypes", "TypeModifier")
    }
    pub fn AccessPolicyAction(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.edgeql.qltypes", "AccessPolicyAction")
    }
    pub fn AccessKind(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.edgeql.qltypes", "AccessKind")
    }
    pub fn TriggerTiming(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.edgeql.qltypes", "TriggerTiming")
    }
    pub fn TriggerKind(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.edgeql.qltypes", "TriggerKind")
    }
    pub fn TriggerScope(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.edgeql.qltypes", "TriggerScope")
    }
    pub fn RewriteKind(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.edgeql.qltypes", "RewriteKind")
    }
    pub fn MigrationGeneratedBy(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.edgeql.qltypes", "MigrationGeneratedBy")
    }
    pub fn IndexDeferrability(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.edgeql.qltypes", "IndexDeferrability")
    }
    pub fn SplatStrategy(py: Python<'_>) -> PyResult<&Bound<'_, PyAny>> {
        static CELL: PyOnceLock<Py<PyAny>> = PyOnceLock::new();
        CELL.import(py, "edb.edgeql.qltypes", "SplatStrategy")
    }
}
