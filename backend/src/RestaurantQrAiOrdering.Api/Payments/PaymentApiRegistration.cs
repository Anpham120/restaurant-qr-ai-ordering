using Microsoft.Extensions.Options;

namespace RestaurantQrAiOrdering.Api.Payments;

public static class PaymentApiRegistration
{
    public static IServiceCollection AddRestaurantPaymentApis(this IServiceCollection services, IConfiguration configuration)
    {
        services.Configure<VietQrOptions>(configuration.GetSection(VietQrOptions.SectionName));
        services.AddSingleton<IVietQrProvider, QrCoderVietQrProvider>();

        return services;
    }
}
