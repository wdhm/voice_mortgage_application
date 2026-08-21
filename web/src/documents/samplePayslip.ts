export type PayslipSampleQuality = "high" | "low";

export function createPayslipSample(quality: PayslipSampleQuality): Promise<File> {
  const canvas = document.createElement("canvas");
  canvas.width = 1200;
  canvas.height = 1600;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Could not create the sample payslip");

  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "#102a43";
  context.fillRect(0, 0, canvas.width, 190);
  context.fillStyle = "#ffffff";
  context.font = "700 54px sans-serif";
  context.fillText("NORTHSTAR AB", 90, 95);
  context.font = "28px sans-serif";
  context.fillText("LÖNESPECIFIKATION / PAYSLIP", 90, 145);

  const lines = [
    ["Employee", "Emma Lindberg"],
    ["Employment", "Permanent full-time"],
    ["Pay period", "August 2026"],
    ["Pay date", "2026-08-25"],
    ["Gross salary", "96 000 SEK"],
    ["Tax", "33 600 SEK"],
    ["Net salary", quality === "high" ? "62 400 SEK" : "[partly obscured]"],
  ];
  context.font = "30px sans-serif";
  lines.forEach(([label, value], index) => {
    const top = 310 + index * 135;
    context.fillStyle = "#627d98";
    context.fillText(label, 90, top);
    context.fillStyle = quality === "low" && index >= 5 ? "rgba(36, 59, 83, 0.3)" : "#243b53";
    context.font = "700 34px sans-serif";
    context.fillText(value, 480, top);
    context.font = "30px sans-serif";
    context.strokeStyle = "#d9e2ec";
    context.beginPath();
    context.moveTo(90, top + 38);
    context.lineTo(1110, top + 38);
    context.stroke();
  });

  context.fillStyle = "#829ab1";
  context.font = "24px sans-serif";
  context.fillText("Fictional document generated for the Bank Alfa demonstration", 90, 1450);

  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error("Could not encode the sample payslip"));
        return;
      }
      resolve(new File([blob], `${quality}-confidence-payslip.png`, { type: "image/png" }));
    }, "image/png");
  });
}