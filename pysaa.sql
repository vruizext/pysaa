/**
 * pysaa.sql
 * script used to create database schema needed by pysaa
 * 
 */
CREATE  DATABASE IF NOT EXISTS `pysaadb` DEFAULT CHARACTER SET utf8;

CREATE TABLE IF NOT EXISTS `pysaadb`.`users` (
	`user_id` INT(10) NOT NULL AUTO_INCREMENT,
	`email` VARCHAR(255) NOT NULL,
	`password` CHAR(32) NOT NULL,
	`status` SMALLINT(1) NOT NULL,
	`role_id` SMALLINT(1)  NOT NULL,
	PRIMARY KEY (`user_id`) )
		DEFAULT CHARACTER SET = utf8;
						
CREATE  TABLE IF NOT EXISTS `pysaadb`.`activations` (
	`user_id` INT(10) NOT NULL,
	`activation_id` CHAR(64) NOT NULL,
	`created` INT(11) NOT NULL,
	PRIMARY KEY (`user_id`) )
		DEFAULT CHARACTER SET = utf8;
						
CREATE  TABLE IF NOT EXISTS `pysaadb`.`logins` (
	`user_id` INT(10) NOT NULL,
	`session_id` CHAR(64)  NULL,
	`attempts` TINYINT(2) NOT NULL,
	`created` INT(11) NOT NULL,
	PRIMARY KEY (`user_id`) )
		DEFAULT CHARACTER SET = utf8;
					
CREATE  TABLE IF NOT EXISTS `pysaadb`.`permissions` (
	`permission_id` INT(10) UNSIGNED NOT NULL,
	`role_id` SMALLINT(1) UNSIGNED NOT NULL,
	`object_id` VARCHAR(255) NOT NULL,
	PRIMARY KEY (`permission_id`) )
		DEFAULT CHARACTER SET = utf8;
					
CREATE  TABLE IF NOT EXISTS `pysaadb`.`roles` (
	`role_id` SMALLINT(1) UNSIGNED NOT NULL ,
	`parent_id` SMALLINT(1) UNSIGNED  NULL ,
	PRIMARY KEY (`role_id`) )
		DEFAULT CHARACTER SET = utf8;
--foreign keys
ALTER TABLE `pysaadb`.`activations` 
	ADD FOREIGN KEY ( `user_id` ) 
	REFERENCES `pyauthdb`.`users` (`user_id`)

ALTER TABLE `pysaadb`.`logins` 
	ADD FOREIGN KEY ( `user_id` ) 
	REFERENCES `pyauthdb`.`users` (`user_id`)

ALTER TABLE `pysaadb`.`users` 
	ADD FOREIGN KEY ( `role_id` )
	REFERENCES `pyauthdb`.`roles` (`role_id`)

ALTER TABLE `pysaadb`.`roles`
	ADD FOREIGN KEY ( `parent_id` )
	REFERENCES `pyauthdb`.`roles` (`role_id`)