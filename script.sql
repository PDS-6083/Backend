delimiter // 
create procedure check_and_delete_aircraft(in aircraft_registration_number varchar(20), out success boolean)
begin
    declare has_flights int;
    declare has_crew_schedules int;
    declare has_engineer_schedules int;

    select count(*) into has_flights from flights where aircraft_registration = aircraft_registration_number;
    select count(*) into has_crew_schedules from crew_schedules where aircraft_registration = aircraft_registration_number;
    select count(*) into has_engineer_schedules from engineer_schedules where aircraft_registration = aircraft_registration_number;

    if has_flights > 0 or has_crew_schedules > 0 or has_engineer_schedules > 0 then
        set success = false;
        return;
        set success = false;
    end if;
    set success = true;
    return;
end //
delimiter ;

call check_and_delete_aircraft('N12345');

