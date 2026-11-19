package com.example.vr_gfriend;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;


@SpringBootApplication
@EnableScheduling
@MapperScan({"com.example.vr_gfriend.user.mapper", "com.example.vr_gfriend.Scheduler.mapper"})
public class VrGfriendApplication {

    public static void main(String[] args) {
        SpringApplication.run(VrGfriendApplication.class, args);
    }
}
