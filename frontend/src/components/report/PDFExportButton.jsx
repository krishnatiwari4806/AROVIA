import React, { useState } from "react";
import { Download, Loader2, Printer } from "lucide-react";
import { exportReportToPDF } from "../../utils/pdfExport";

/**
 * PDF Export and Print Action Buttons.
 */
export default function PDFExportButton({ targetRole = "Role", sessionId = "session", containerId = "report-card-container" }) {
  const [isExporting, setIsExporting] = useState(false);

  const handleDownloadPDF = async () => {
    setIsExporting(true);
    const dateStr = new Date().toISOString().split("T")[0];
    const cleanRole = (targetRole || "Interview").replace(/[^a-zA-Z0-9]/g, "_");
    const fileName = `AROVIA_Report_${cleanRole}_${dateStr}.pdf`;

    try {
      await exportReportToPDF(containerId, fileName);
    } finally {
      setIsExporting(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="action-btn-group">
      <button
        onClick={handleDownloadPDF}
        disabled={isExporting}
        className="btn btn-primary"
        title="Download high-resolution multi-page PDF"
      >
        {isExporting ? (
          <>
            <Loader2 size={16} className="spinner-icon" />
            <span>Generating PDF...</span>
          </>
        ) : (
          <>
            <Download size={16} />
            <span>Download PDF Report</span>
          </>
        )}
      </button>

      <button
        onClick={handlePrint}
        className="btn btn-secondary"
        title="Open browser print dialog"
      >
        <Printer size={16} />
        <span>Print</span>
      </button>
    </div>
  );
}
