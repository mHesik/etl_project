SELECT категория, sum(количество) as Общее_кол_во, ROUND(sum(количество * цена), 2) as Общая_стоим_ть
From products p 
group by категория
ORDER BY Общее_кол_во DESC