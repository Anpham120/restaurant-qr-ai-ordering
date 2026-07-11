import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { loadOrderContext } from "../components/customer/customerMenuStorage";
import { orderingPath } from "./orderingRoutes";

export function LegacyOrderingRedirect({ destination }: { destination: string }) {
  const navigate = useNavigate();

  useEffect(() => {
    const context = loadOrderContext();
    if (context.sessionId && context.sessionToken) {
      navigate(orderingPath(context.sessionId, destination), { replace: true });
    }
  }, [destination, navigate]);

  return (
    <main className="ordering-state">
      <p className="ordering-state-kicker">CMC Restaurant</p>
      <h1>Quét QR để gọi món</h1>
      <p>Vui lòng quét QR tại bàn để sử dụng AI tư vấn, giỏ hàng và thanh toán.</p>
      <a href="/">Về trang giới thiệu</a>
    </main>
  );
}

export function LegacyOrderTrackingRedirect() {
  const { orderCode } = useParams();
  return <LegacyOrderingRedirect destination={orderCode ? `orders/${orderCode}` : "orders"} />;
}
