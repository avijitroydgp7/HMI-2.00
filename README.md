# HMI-2.00

## Building

Install dependencies and compile the C++ helper before packaging or running the application:

```bash
pip install -r requirements.txt
cmake -S cpp -B cpp/build -Dpybind11_DIR=$(python -m pybind11 --cmakedir)
cmake --build cpp/build --config Release
```

This produces a `scene_utils` extension module in the project root used by `design_canvas.py` for fast snapping. If the module is unavailable, a slower Python fallback is used.