FROM nginx:1.27-alpine

# remove nginx's default conf file
RUN rm /etc/nginx/conf.d/default.conf

COPY app.conf.template /etc/nginx/templates/app.conf.template

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]