FROM nginx:1.25-alpine

# Remove default configuration
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy custom configurations
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/default.conf /etc/nginx/conf.d/default.conf

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -q -O - http://localhost/health-nginx || exit 1

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
