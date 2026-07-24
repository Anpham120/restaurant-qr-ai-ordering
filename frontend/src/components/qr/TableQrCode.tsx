import { useEffect, useState } from "react";
import QRCode from "qrcode";

type TableQrCodeProps = {
  value: string;
  label: string;
  downloadName: string;
};

export function TableQrCode({ value, label, downloadName }: TableQrCodeProps) {
  const [dataUrl, setDataUrl] = useState<string | null>(null);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    let isMounted = true;

    QRCode.toDataURL(value, { width: 240, margin: 1, errorCorrectionLevel: "M" })
      .then((url) => {
        if (isMounted) {
          setDataUrl(url);
          setHasError(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setHasError(true);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [value]);

  if (hasError) {
    return (
      <div className="table-qr-image is-error" role="img" aria-label={`${label} (lỗi)`}>
        Lỗi tạo QR
      </div>
    );
  }

  if (!dataUrl) {
    return <div className="table-qr-image is-loading" role="img" aria-label={`${label} (đang tạo)`} />;
  }

  return (
    <div className="table-qr-image">
      <img alt={label} src={dataUrl} />
      <a className="table-qr-download" download={downloadName} href={dataUrl}>
        Tải QR
      </a>
    </div>
  );
}
