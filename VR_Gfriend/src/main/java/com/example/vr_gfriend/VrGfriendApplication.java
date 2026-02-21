package com.example.vr_gfriend;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;


@SpringBootApplication
@MapperScan("com.example.vr_gfriend") // <--- 必须确保路径指向 UserMapper 所在的包
public class VrGfriendApplication {

    public static void main(String[] args) {
        SpringApplication.run(VrGfriendApplication.class, args);
    }
}
