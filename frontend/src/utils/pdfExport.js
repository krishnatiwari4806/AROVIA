/**
 * Client-Side PDF Export Utility using jsPDF and html2canvas (₹0 Zero Cost).
 */

import html2canvas from "html2canvas";
import jsPDF from "jspdf";

/**
 * Generate and trigger direct download of a multi-page A4 PDF report.
 *
 * @param {string} elementId - DOM element ID to render into PDF
 * @param {string} [fileName="AROVIA_Interview_Report.pdf"] - Target file download name
 * @returns {Promise<boolean>} - Resolves true on success, false on error
 */
export async function exportReportToPDF(elementId, fileName = "AROVIA_Interview_Report.pdf") {
  const element = document.getElementById(elementId);
  if (!element) {
    console.error(`PDF Export Error: Element with id #${elementId} not found.`);
    return false;
  }

  try {
    // 1. Temporarily expand all accordions if needed for full PDF capture
    const expandedDetails = element.querySelectorAll(".turn-accordion-card");
    const wasExpandedStates = [];
    expandedDetails.forEach((card) => {
      wasExpandedStates.push(card.classList.contains("expanded"));
      card.classList.add("expanded");
    });

    // 2. Render DOM to high-DPI canvas
    const canvas = await html2canvas(element, {
      scale: 2, // 2x for sharp text and crisp radar polygons
      useCORS: true,
      logging: false,
      backgroundColor: "#0a0d14", // Dark theme background
      windowWidth: element.scrollWidth,
    });

    // 3. Revert accordion states
    expandedDetails.forEach((card, idx) => {
      if (!wasExpandedStates[idx]) {
        card.classList.remove("expanded");
      }
    });

    // 4. Calculate multi-page A4 dimensions in mm
    const imgData = canvas.toDataURL("image/png");
    const pdf = new jsPDF("p", "mm", "a4");
    const pdfWidth = 210; // A4 width in mm
    const pdfHeight = 297; // A4 height in mm
    const imgHeight = (canvas.height * pdfWidth) / canvas.width;

    let heightLeft = imgHeight;
    let position = 0;

    // Add first page
    pdf.addImage(imgData, "PNG", 0, position, pdfWidth, imgHeight);
    heightLeft -= pdfHeight;

    // Add subsequent pages if content exceeds A4 height
    while (heightLeft > 0) {
      position = heightLeft - imgHeight;
      pdf.addPage();
      pdf.addImage(imgData, "PNG", 0, position, pdfWidth, imgHeight);
      heightLeft -= pdfHeight;
    }

    // 5. Trigger direct browser download
    pdf.save(fileName);
    return true;
  } catch (error) {
    console.error("Failed to generate PDF via canvas:", error);
    // Graceful fallback to browser print dialog
    window.print();
    return false;
  }
}
