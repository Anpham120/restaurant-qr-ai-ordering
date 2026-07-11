FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

COPY backend/RestaurantQrAiOrdering.csproj backend/
COPY backend/src/RestaurantQrAiOrdering.Api/RestaurantQrAiOrdering.Api.csproj backend/src/RestaurantQrAiOrdering.Api/
RUN dotnet restore backend/src/RestaurantQrAiOrdering.Api/RestaurantQrAiOrdering.Api.csproj

COPY backend/ backend/
RUN dotnet publish backend/src/RestaurantQrAiOrdering.Api/RestaurantQrAiOrdering.Api.csproj \
    --configuration Release \
    --output /app/publish \
    /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

ENV ASPNETCORE_URLS=http://+:8080
ENV ASPNETCORE_ENVIRONMENT=Production

EXPOSE 8080

COPY --from=build --chown=app:app /app/publish .
USER app
ENTRYPOINT ["dotnet", "RestaurantQrAiOrdering.Api.dll"]
