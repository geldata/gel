use gel_schema::ObjectListTy;
use pyo3::{
    exceptions,
    prelude::*,
    types::{PySequence, PyTuple, PyType},
};
use std::sync::Arc;
use uuid::Uuid;

use crate::imports;

#[pyclass(frozen, module = "edb.schema._schema")]
#[derive(Clone)]
struct ObjectList {
    inner: Arc<gel_schema::ObjectList>,
}

impl ObjectList {
    fn new_of_cls(py: Python<'_>, cls: &Bound<'_, PyType>, values: Vec<Uuid>) -> PyResult<Self> {
        let func_param_list = imports::FuncParameterList(py)?;
        let ty = if cls.is_subclass(func_param_list)? {
            ObjectListTy::FuncParameterList
        } else {
            ObjectListTy::ObjectList
        };

        let inner = Arc::new(gel_schema::ObjectList {
            ty,
            value_ty: None,
            values,
        });
        Ok(Self { inner })
    }
}

#[pymethods]
impl ObjectList {
    fn __repr__(&self) -> String {
        format!("{:?}", self.inner)
    }

    fn __len__(&self) -> usize {
        self.inner.values.len()
    }

    fn __eq__(&self, other: &ObjectList) -> bool {
        self.inner.values == other.inner.values
    }

    #[classmethod]
    fn create<'p>(
        cls: &Bound<'p, PyType>,
        py: Python<'p>,
        _schema: &crate::Schema,
        ids: Bound<'_, PySequence>,
    ) -> PyResult<Self> {
        let values = ids
            .try_iter()?
            .map(|x| x?.extract::<Uuid>())
            .collect::<Result<_, _>>()?;
        ObjectList::new_of_cls(py, cls, values)
    }

    #[classmethod]
    fn create_empty<'p>(cls: &Bound<'p, PyType>, py: Python<'p>) -> PyResult<Self> {
        ObjectList::new_of_cls(py, cls, Vec::new())
    }

    fn ids<'p>(&self, py: Python<'p>) -> PyResult<Bound<'p, PyTuple>> {
        PyTuple::new(py, &self.inner.values)
    }

    fn objects<'p>(&self, py: Python<'p>, schema: &crate::Schema) -> PyResult<Bound<'p, PyTuple>> {
        let mut objects_py = Vec::with_capacity(self.inner.values.len());
        for id in &self.inner.values {
            objects_py.push(schema.get_by_id(py, id.clone())?.unwrap());
        }
        PyTuple::new(py, objects_py)
    }

    fn first<'p>(
        &self,
        py: Python<'p>,
        schema: &crate::Schema,
        default: Bound<'p, PyAny>,
    ) -> PyResult<Bound<'p, PyAny>> {
        if let Some(id) = self.inner.values.first() {
            Ok(schema.get_by_id(py, id.clone())?.unwrap())
        } else {
            if default.is_none() {
                return Err(exceptions::PyIndexError::new_err("ObjectList is empty"));
            } else {
                return Ok(default);
            }
        }
    }
}
