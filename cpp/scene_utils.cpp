#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <cmath>

namespace py = pybind11;

struct BoundingBox {
    double left;
    double top;
    double right;
    double bottom;
};

py::tuple snap_to_objects(const std::vector<BoundingBox>& boxes,
                         double cursor_x,
                         double cursor_y,
                         double threshold) {
    double snap_x = cursor_x;
    double snap_y = cursor_y;
    double best_dx = threshold;
    double best_dy = threshold;
    bool have_x = false;
    bool have_y = false;
    double line_x = 0.0;
    double line_y = 0.0;

    for (const auto& b : boxes) {
        double x_vals[3] = {b.left, (b.left + b.right) / 2.0, b.right};
        for (double xv : x_vals) {
            double dx = std::abs(cursor_x - xv);
            if (dx < best_dx) {
                best_dx = dx;
                snap_x = xv;
                line_x = xv;
                have_x = true;
            }
        }
        double y_vals[3] = {b.top, (b.top + b.bottom) / 2.0, b.bottom};
        for (double yv : y_vals) {
            double dy = std::abs(cursor_y - yv);
            if (dy < best_dy) {
                best_dy = dy;
                snap_y = yv;
                line_y = yv;
                have_y = true;
            }
        }
    }

    py::object lx = have_x ? py::object(py::float_(line_x)) : py::object(py::none());
    py::object ly = have_y ? py::object(py::float_(line_y)) : py::object(py::none());
    return py::make_tuple(snap_x, snap_y, lx, ly);
}

PYBIND11_MODULE(scene_utils, m) {
    m.doc() = "Scene utility helpers";
    py::class_<BoundingBox>(m, "BoundingBox")
        .def(py::init<double,double,double,double>())
        .def_readwrite("left", &BoundingBox::left)
        .def_readwrite("top", &BoundingBox::top)
        .def_readwrite("right", &BoundingBox::right)
        .def_readwrite("bottom", &BoundingBox::bottom);
    m.def("snap_to_objects", &snap_to_objects,
          py::arg("boxes"), py::arg("cursor_x"), py::arg("cursor_y"), py::arg("threshold"),
          "Compute snapped position and guideline coordinates");
}