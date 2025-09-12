use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict, PyInt, PyString, PyType};

use edb_graphql_parser::position::Pos;

use crate::py_token::{self, PyToken};
use crate::rewrite::{self, Value};

#[pyclass]
pub struct Entry {
    #[pyo3(get)]
    key: Py<PyAny>,
    #[pyo3(get)]
    variables: Py<PyAny>,
    #[pyo3(get)]
    substitutions: Py<PyAny>,
    _tokens: Vec<PyToken>,
    _end_pos: Pos,
    #[pyo3(get)]
    num_variables: usize,

    orig_entry: rewrite::Entry,
}

#[pymethods]
impl Entry {
    fn tokens<'py>(&self, py: Python<'py>, kinds: Py<PyAny>) -> PyResult<impl IntoPyObject<'py>> {
        py_token::convert_tokens(py, &self._tokens, &self._end_pos, kinds)
    }

    fn pack(&self, py: Python) -> PyResult<Py<PyAny>> {
        let mut buf = vec![1u8]; // type and version
        bincode::serialize_into(&mut buf, &self.orig_entry)
            .map_err(|e| PyValueError::new_err(format!("Failed to pack: {e}")))?;
        Ok(PyBytes::new(py, buf.as_slice()).into())
    }
}

#[pyfunction]
pub fn unpack(py: Python<'_>, serialized: &Bound<PyBytes>) -> PyResult<Py<PyAny>> {
    let buf = serialized.as_bytes();
    match buf[0] {
        1u8 => {
            let pack: rewrite::Entry = bincode::deserialize(&buf[1..])
                .map_err(|e| PyValueError::new_err(format!("Failed to unpack: {e}")))?;
            let entry = convert_entry(py, pack)?;
            entry.into_pyobject(py).map(|e| e.unbind().into_any())
        }
        _ => Err(PyValueError::new_err(format!(
            "Invalid type/version byte: {}",
            buf[0]
        ))),
    }
}

pub fn convert_entry(py: Python<'_>, entry: rewrite::Entry) -> PyResult<Entry> {
    // import decimal
    let decimal_cls = PyModule::import(py, "decimal")?.getattr("Decimal")?;

    let vars = PyDict::new(py);
    let substitutions = PyDict::new(py);
    for (idx, var) in entry.variables.iter().enumerate() {
        let s = format!("__edb_arg_{}", idx).into_pyobject(py)?;

        vars.set_item(&s, value_to_py(py, &var.value, &decimal_cls)?)?;
        substitutions.set_item(
            s,
            (
                &var.token.value,
                var.token.position.map(|x| x.line),
                var.token.position.map(|x| x.column),
            ),
        )?;
    }
    for (name, var) in &entry.defaults {
        vars.set_item(name, value_to_py(py, &var.value, &decimal_cls)?)?
    }
    let orig_entry = entry.clone();
    Ok(Entry {
        key: PyString::new(py, &entry.key).into(),
        variables: vars.into_pyobject(py)?.into(),
        substitutions: substitutions.into(),
        _tokens: entry.tokens,
        _end_pos: entry.end_pos,
        num_variables: entry.num_variables,
        orig_entry,
    })
}

fn value_to_py(py: Python, value: &Value, decimal_cls: &Bound<PyAny>) -> PyResult<Py<PyAny>> {
    let v = match value {
        Value::Str(ref v) => PyString::new(py, v).into_any(),
        Value::Int32(v) => v.into_pyobject(py)?.into_any(),
        Value::Int64(v) => v.into_pyobject(py)?.into_any(),
        Value::Decimal(v) => decimal_cls.call((v.as_str(),), None)?.into_any(),
        Value::BigInt(ref v) => PyType::new::<PyInt>(py)
            .call((v.as_str(),), None)?
            .into_any(),
        Value::Boolean(b) => b.into_pyobject(py)?.to_owned().into_any(),
    };
    Ok(v.into())
}
