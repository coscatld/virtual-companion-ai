package com.example.vr_gfriend.common.config;

import com.fasterxml.jackson.annotation.JsonAutoDetect;
import com.fasterxml.jackson.annotation.PropertyAccessor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.Jackson2JsonRedisSerializer;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.net.UnknownHostException;

@Configuration
public class RedisConfig {
    //JDK->JSON
    @Bean
    @SuppressWarnings("all")
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) throws UnknownHostException {
        //str,obj
        RedisTemplate<String, Object> template = new RedisTemplate<String, Object>();
        template.setConnectionFactory(factory);
        //序列化配置1.key保证看见str，2.value保证看见json
        Jackson2JsonRedisSerializer Serializer = new Jackson2JsonRedisSerializer(Object.class);//注册json序列化
        ObjectMapper om = new ObjectMapper();//检查器
        om.setVisibility(PropertyAccessor.ALL, JsonAutoDetect.Visibility.ANY);//1.检查字段，2.全部序列化
        om.enableDefaultTyping(ObjectMapper.DefaultTyping.NON_FINAL);
        Serializer.setObjectMapper(om);//注入序列化工具
        StringRedisSerializer stringRedisSerializer = new StringRedisSerializer();//注册str序列化
        template.setKeySerializer(stringRedisSerializer);//key采用str序列化
        template.setHashKeySerializer(stringRedisSerializer);//hash的key采用str序列化
        template.setValueSerializer(Serializer);//value采用json
        template.setHashValueSerializer(Serializer);//hash采用json
        template.afterPropertiesSet();
        return template;
    }
}
