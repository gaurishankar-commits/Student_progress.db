/**
 * ==============================================================================
 * Student Academic Progression and Portfolio Management System
 * Frontend Client Controller & Dynamic Chart.js Handler (main.js)
 * ==============================================================================
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Initialize Bootstrap Tooltips if available
  if (typeof bootstrap !== "undefined" && bootstrap.Tooltip) {
    const tooltipTriggerList = [].slice.call(
      document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
  }

  // 2. Initialize Progression Chart if element exists
  initProgressionChart();

  // 3. Dynamic Grade Point Calculator in Subject Marks Modal
  setupMarksCalculator();
});

/**
 * Initializes the Chart.js line graph plotting SGPA & CGPA vs Semester.
 * - Enforces 0 to 10 Y-axis grade-point scale
 * - Accurately plots semester progression
 * - Detects and labels missing semesters
 * - Highlights recorded gap years
 */
function initProgressionChart() {
  const chartCanvas = document.getElementById("progressionChart");
  if (!chartCanvas) return;

  // Retrieve chart payload injected from Flask view
  const rawData = chartCanvas.getAttribute("data-chart");
  if (!rawData) return;

  let chartData;
  try {
    chartData = JSON.parse(rawData);
  } catch (e) {
    console.error("Could not parse chart data JSON:", e);
    return;
  }

  const ctx = chartCanvas.getContext("2d");

  // Build labels and aligned dataset arrays for semesters 1 through max_sem
  const semesters = chartData.semesters || [];
  if (semesters.length === 0) {
    chartCanvas.parentElement.innerHTML = `
      <div class="text-center py-5 text-muted">
        <i class="bi bi-graph-up-arrow fs-1 d-block mb-2 text-secondary"></i>
        <p class="mb-0">No semester performance records available yet.</p>
        <small>Add Semester 1 to generate academic progression analytics.</small>
      </div>`;
    return;
  }

  const semMap = {};
  semesters.forEach((s) => {
    semMap[s.semester_no] = s;
  });

  const maxSemNo = Math.max(...semesters.map((s) => s.semester_no), 1);
  const labels = [];
  const sgpaSeries = [];
  const cgpaSeries = [];

  for (let sem = 1; sem <= maxSemNo; sem++) {
    labels.push(`Semester ${sem}`);
    if (semMap[sem]) {
      sgpaSeries.push(semMap[sem].sgpa);
      cgpaSeries.push(semMap[sem].cgpa);
    } else {
      // Gap or missing semester record
      sgpaSeries.push(null);
      cgpaSeries.push(null);
    }
  }

  new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "SGPA (Semester Grade Point)",
          data: sgpaSeries,
          borderColor: "#0d9488", // Teal
          backgroundColor: "rgba(13, 148, 136, 0.1)",
          borderWidth: 3,
          pointBackgroundColor: "#0d9488",
          pointBorderColor: "#ffffff",
          pointBorderWidth: 2,
          pointRadius: 6,
          pointHoverRadius: 8,
          tension: 0.3,
          spanGaps: false, // Intentionally breaks line to show missing semesters!
        },
        {
          label: "CGPA (Cumulative Grade Point)",
          data: cgpaSeries,
          borderColor: "#1e3a8a", // Navy
          backgroundColor: "rgba(30, 58, 138, 0.05)",
          borderWidth: 3,
          borderDash: [5, 5],
          pointBackgroundColor: "#1e3a8a",
          pointBorderColor: "#ffffff",
          pointBorderWidth: 2,
          pointRadius: 6,
          pointHoverRadius: 8,
          tension: 0.3,
          spanGaps: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: {
          position: "top",
          labels: {
            usePointStyle: true,
            boxWidth: 8,
            font: {
              size: 13,
              family: "'Segoe UI', system-ui, sans-serif",
              weight: "600",
            },
          },
        },
        tooltip: {
          backgroundColor: "#0f172a",
          titleFont: { size: 13, weight: "bold" },
          bodyFont: { size: 12 },
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            label: function (context) {
              const val = context.parsed.y;
              if (val === null || val === undefined) {
                return `${context.dataset.label}: Record Missing`;
              }
              return `${context.dataset.label}: ${val.toFixed(2)} / 10.00`;
            },
          },
        },
      },
      scales: {
        y: {
          min: 0,
          max: 10,
          ticks: {
            stepSize: 1,
            font: { size: 12 },
            callback: function (value) {
              return value + ".0";
            },
          },
          grid: {
            color: "#f1f5f9",
          },
          title: {
            display: true,
            text: "Grade Point (10.0 Scale)",
            font: { weight: "600", size: 12 },
          },
        },
        x: {
          grid: {
            display: false,
          },
          ticks: {
            font: { weight: "600", size: 12 },
          },
        },
      },
    },
  });
}

/**
 * Automatically computes Grade Point = (marks_obtained / max_marks) * 10
 * as the user types in the Add Subject Marks modal.
 */
function setupMarksCalculator() {
  const marksObt = document.getElementById("inputMarksObtained");
  const maxMarks = document.getElementById("inputMaxMarks");
  const gradePt = document.getElementById("inputGradePoint");

  if (!marksObt || !maxMarks || !gradePt) return;

  function calculate() {
    const obt = parseFloat(marksObt.value);
    const max = parseFloat(maxMarks.value);
    if (!isNaN(obt) && !isNaN(max) && max > 0 && obt >= 0 && obt <= max) {
      const calcGp = (obt / max) * 10.0;
      gradePt.value = calcGp.toFixed(2);
    }
  }

  marksObt.addEventListener("input", calculate);
  maxMarks.addEventListener("input", calculate);
}

/**
 * Pre-populates the Add Marks modal with the specific semester ID.
 */
function openAddMarksModal(semesterId, semesterNo) {
  const modalEl = document.getElementById("addMarksModal");
  if (!modalEl) return;

  const form = document.getElementById("addMarksForm");
  if (form) {
    form.action = `/semesters/${semesterId}/marks/add`;
  }

  const titleEl = document.getElementById("addMarksSemesterTitle");
  if (titleEl) {
    titleEl.textContent = `Semester ${semesterNo}`;
  }

  const modalInstance = new bootstrap.Modal(modalEl);
  modalInstance.show();
}

/**
 * Pre-populates the Edit Semester modal.
 */
function openEditSemesterModal(sem) {
  const modalEl = document.getElementById("editSemesterModal");
  if (!modalEl) return;

  const form = document.getElementById("editSemesterForm");
  if (form) {
    form.action = `/semesters/${sem.id}/edit`;
  }

  document.getElementById("editSemNo").value = sem.semester_no;
  document.getElementById("editAcYear").value = sem.academic_year || "";
  document.getElementById("editSgpa").value = sem.sgpa !== null ? sem.sgpa : "";
  document.getElementById("editCgpa").value = sem.cgpa !== null ? sem.cgpa : "";
  document.getElementById("editStatus").value = sem.status || "Completed";
  document.getElementById("editRemarks").value = sem.remarks || "";

  const modalInstance = new bootstrap.Modal(modalEl);
  modalInstance.show();
}
