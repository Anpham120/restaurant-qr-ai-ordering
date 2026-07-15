using RestaurantQrAiOrdering.Enums;

namespace RestaurantQrAiOrdering.Api.Tables;

public enum TableSessionResumeState
{
    New,
    CartPending,
    OrderInProgress,
    ReadyForPayment,
    PaymentPending,
    Paid
}

public static class TableSessionResumeStateResolver
{
    public static TableSessionResumeState Resolve(
        int cartItemCount,
        IReadOnlyCollection<OrderStatus> orderStatuses,
        PaymentStatus? invoiceStatus)
    {
        if (invoiceStatus is PaymentStatus.Paid or PaymentStatus.Confirmed)
        {
            return TableSessionResumeState.Paid;
        }

        if (invoiceStatus == PaymentStatus.Pending)
        {
            return TableSessionResumeState.PaymentPending;
        }

        var activeOrderStatuses = orderStatuses
            .Where(status => status != OrderStatus.Cancelled)
            .ToArray();

        if (activeOrderStatuses.Length == 0)
        {
            return cartItemCount > 0
                ? TableSessionResumeState.CartPending
                : TableSessionResumeState.New;
        }

        if (activeOrderStatuses.Any(status => status is
            OrderStatus.Draft or
            OrderStatus.Placed or
            OrderStatus.Confirmed or
            OrderStatus.Preparing or
            OrderStatus.Ready))
        {
            return TableSessionResumeState.OrderInProgress;
        }

        return TableSessionResumeState.ReadyForPayment;
    }
}
