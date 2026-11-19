package com.example.vr_gfriend.common.Interceptor;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpHeaders;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {
    private final JwtInterceptor jwtInterceptor;
    private final String[] allowedOrigins;

    public WebConfig(JwtInterceptor jwtInterceptor, @Value("${ga.web.allowed-origins}") String[] allowedOrigins) {
        this.jwtInterceptor = jwtInterceptor;
        this.allowedOrigins = allowedOrigins;
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(jwtInterceptor)
                .addPathPatterns("/api/**", "/admin/user/**", "/internal/**")
                .excludePathPatterns("/admin/user/register", "/admin/user/login");
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**").allowedOrigins(allowedOrigins).allowedMethods("GET", "POST")
                .exposedHeaders(HttpHeaders.RETRY_AFTER);
        registry.addMapping("/admin/user/**").allowedOrigins(allowedOrigins).allowedMethods("GET", "POST");
    }
}
