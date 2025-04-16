use std::convert::TryFrom;

use bigdecimal::Num;

use bytes::{BufMut, Bytes, BytesMut};
use edgeql_parser::tokenizer::Value;
use gel_protocol::codec;
use gel_protocol::model::{BigInt, Decimal};
use pyo3::exceptions::{PyAssertionError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict, PyFloat, PyInt, PyList, PyString, PyTuple};

use crate::errors::SyntaxError;
use crate::normalize::{normalize as _normalize, Error, PackedEntry, Variable};
use crate::tokenizer::tokens_to_py;

#[pyfunction]
pub fn normalize(py: Python<'_>, text: &Bound<PyString>) -> PyResult<Entry> {
    let text = text.to_string();
    match _normalize(&text) {
        Ok(entry) => Entry::new(py, entry),
        Err(Error::Tokenizer(msg, pos)) => Err(SyntaxError::new_err((
            msg,
            (pos, py.None()),
            py.None(),
            py.None(),
        ))),
        Err(Error::Assertion(msg, pos)) => {
            Err(PyAssertionError::new_err(format!("{}: {}", pos, msg)))
        }
    }
}

#[pyclass]
pub struct Entry {
    #[pyo3(get)]
    key: PyObject,

    #[pyo3(get)]
    tokens: PyObject,

    #[pyo3(get)]
    extra_blobs: PyObject,

    extra_named: bool,

    #[pyo3(get)]
    first_extra: Option<usize>,

    #[pyo3(get)]
    extra_counts: PyObject,

    entry_pack: PackedEntry,
}

impl Entry {
    pub fn new(py: Python, entry: crate::normalize::Entry) -> PyResult<Self> {
        let blobs = serialize_all(py, &entry.variables)?;
        let counts = entry.variables.iter().map(|x| x.len());

        Ok(Entry {
            key: PyBytes::new(py, &entry.hash[..]).into(),
            tokens: tokens_to_py(py, entry.tokens.clone())?.into_any(),
            extra_blobs: blobs.into(),
            extra_named: entry.named_args,
            first_extra: entry.first_arg,
            extra_counts: PyList::new(py, counts)?.into(),
            entry_pack: entry.into(),
        })
    }
}

#[pymethods]
impl Entry {
    fn get_variables(&self, py: Python) -> PyResult<PyObject> {
        let vars = PyDict::new(py);
        for (param_name, _, _, value) in VariableNameIter::new(self) {
            vars.set_item(param_name, TokenizerValue(value))?;
        }

        Ok(vars.into())
    }

    // This function returns a dictionary mapping normalized parameter names to their blob and var indexes.
    fn get_extra_variable_indexes(&self, py: Python) -> PyResult<PyObject> {
        let indexes = PyDict::new(py);
        for (param_name, blob_index, var_index, _) in VariableNameIter::new(self) {
            indexes.set_item(param_name, PyTuple::new(py, [blob_index, var_index])?)?;
        }

        Ok(indexes.into())
    }

    fn pack(&self, py: Python) -> PyResult<PyObject> {
        let mut buf = vec![1u8]; // type and version
        bincode::serialize_into(&mut buf, &self.entry_pack)
            .map_err(|e| PyValueError::new_err(format!("Failed to pack: {e}")))?;
        Ok(PyBytes::new(py, buf.as_slice()).into())
    }
}

struct VariableNameIter<'a> {
    entry_pack: &'a PackedEntry,
    first_extra: Option<usize>,
    extra_named: bool,
    name_index: usize,
    blob_index: usize,
    var_index: usize,
}

impl<'a> VariableNameIter<'a> {
    pub fn new(entry: &'a Entry) -> Self {
        VariableNameIter {
            entry_pack: &entry.entry_pack,
            first_extra: entry.first_extra,
            extra_named: entry.extra_named,
            name_index: 0,
            blob_index: 0,
            var_index: 0,
        }
    }
}

impl<'a> Iterator for VariableNameIter<'a> {
    type Item = (String, usize, usize, &'a Value);

    fn next(&mut self) -> Option<Self::Item> {
        // Check termination
        let first = self.first_extra?;
        if self.blob_index >= self.entry_pack.variables.len() {
            return None;
        }
        if self.var_index >= self.entry_pack.variables[self.blob_index].len() {
            return None;
        }

        // Get result
        let blob_vars = self.entry_pack.variables.get(self.blob_index)?;

        let name = if self.extra_named {
            format!("__edb_arg_{}", first + self.name_index)
        } else {
            (first + self.name_index).to_string()
        };

        let result = (
            name,
            self.blob_index,
            self.var_index,
            &blob_vars[self.var_index].value,
        );

        // Advance indexes
        self.var_index += 1;
        if self.var_index >= blob_vars.len() {
            self.var_index = 0;
            self.blob_index += 1;
        }
        self.name_index += 1;

        Some(result)
    }
}

pub fn serialize_extra(variables: &[Variable]) -> Result<Bytes, String> {
    use gel_protocol::codec::Codec;
    use gel_protocol::value::Value as P;

    let mut buf = BytesMut::new();
    buf.reserve(4 * variables.len());
    for var in variables {
        buf.reserve(4);
        let pos = buf.len();
        buf.put_u32(0); // replaced after serializing a value
        match var.value {
            Value::Int(v) => {
                codec::Int64
                    .encode(&mut buf, &P::Int64(v))
                    .map_err(|e| format!("int cannot be encoded: {}", e))?;
            }
            Value::String(ref v) => {
                codec::Str
                    .encode(&mut buf, &P::Str(v.clone()))
                    .map_err(|e| format!("str cannot be encoded: {}", e))?;
            }
            Value::Float(ref v) => {
                codec::Float64
                    .encode(&mut buf, &P::Float64(*v))
                    .map_err(|e| format!("float cannot be encoded: {}", e))?;
            }
            Value::BigInt(ref v) => {
                // We have two different versions of BigInt implementations here.
                // We have to use bigdecimal::num_bigint::BigInt because it can parse with radix 16.

                let val = bigdecimal::num_bigint::BigInt::from_str_radix(v, 16)
                    .map_err(|e| format!("bigint cannot be encoded: {}", e))
                    .and_then(|x| {
                        BigInt::try_from(x).map_err(|e| format!("bigint cannot be encoded: {}", e))
                    })?;

                codec::BigInt
                    .encode(&mut buf, &P::BigInt(val))
                    .map_err(|e| format!("bigint cannot be encoded: {}", e))?;
            }
            Value::Decimal(ref v) => {
                let val = Decimal::try_from(v.clone())
                    .map_err(|e| format!("decimal cannot be encoded: {}", e))?;
                codec::Decimal
                    .encode(&mut buf, &P::Decimal(val))
                    .map_err(|e| format!("decimal cannot be encoded: {}", e))?;
            }
            Value::Bytes(_) => {
                // bytes literals should not be extracted during normalization
                unreachable!()
            }
        }
        let len = buf.len() - pos - 4;
        buf[pos..pos + 4].copy_from_slice(
            &u32::try_from(len)
                .map_err(|_| "element isn't too long".to_owned())?
                .to_be_bytes(),
        );
    }
    Ok(buf.freeze())
}

pub fn serialize_all<'a>(
    py: Python<'a>,
    variables: &[Vec<Variable>],
) -> PyResult<Bound<'a, PyList>> {
    let mut buf = Vec::with_capacity(variables.len());
    for vars in variables {
        let bytes = serialize_extra(vars).map_err(PyAssertionError::new_err)?;
        buf.push(PyBytes::new(py, &bytes));
    }
    PyList::new(py, &buf)
}

/// Newtype required to define a trait for a foreign type.
pub struct TokenizerValue<'a>(pub &'a Value);

impl<'py> IntoPyObject<'py> for TokenizerValue<'py> {
    type Target = PyAny;
    type Output = Bound<'py, Self::Target>;
    type Error = PyErr;

    fn into_pyobject(self, py: Python<'py>) -> PyResult<Self::Output> {
        let res = match self.0 {
            Value::Int(v) => v.into_pyobject(py)?.into_any(),
            Value::String(v) => v.into_pyobject(py)?.into_any(),
            Value::Float(v) => v.into_pyobject(py)?.into_any(),
            Value::BigInt(v) => py.get_type::<PyInt>().call((v, 16), None)?,
            Value::Decimal(v) => py
                .get_type::<PyFloat>()
                .call((v.to_string(),), None)?
                .into_any(),
            Value::Bytes(v) => PyBytes::new(py, v).into_any(),
        };
        Ok(res)
    }
}
