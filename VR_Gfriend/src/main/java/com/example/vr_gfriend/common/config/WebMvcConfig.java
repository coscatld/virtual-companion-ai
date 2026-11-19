package com.example.vr_gfriend.common.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.task.AsyncTaskExecutor;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.web.servlet.config.annotation.AsyncSupportConfigurer;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration(proxyBeanMethods = false)
public class WebMvcConfig {
    @Bean
    public ThreadPoolTaskExecutor streamTaskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(8);
        executor.setMaxPoolSize(40);
        executor.setQueueCapacity(100);
        executor.setThreadNamePrefix("ga-stream-");
        return executor;
    }

    @Bean
    public WebMvcConfigurer asyncMvcConfigurer(AsyncTaskExecutor streamTaskExecutor) {
        return new WebMvcConfigurer() {
            @Override
            public void configureAsyncSupport(AsyncSupportConfigurer configurer) {
                configurer.setTaskExecutor(streamTaskExecutor);
                configurer.setDefaultTimeout(125_000L);
            }
        };
    }
}
