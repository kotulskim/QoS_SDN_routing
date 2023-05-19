Uruchom maszynę wirtualną za pomocą obrazu .ova, który dostępny jest pod linkiem https://1drv.ms/u/s!Ap6kVIPgofkWhNEJ1AQ4ueuSnGIhQA?e=qTNz3c

Zaloguj się na konto student za pomocą hasła: @mininet

Przejdź do katalogu QoS_SDN_routing

Uruchom skrypty pythona w osobnych oknach terminala za pomocą komend:

$ sudo python routing_net.py

$ sudo python ./pox.py routing_controller.py

W celu przetestwania działania routingu uruchom ping między hostami h1, h2, h3 a hostami h4, h5, h6 w terminalu mininet:
mininet> h1 ping h5

Zaobserwuj działanie kontrollera SDN.

Pełny opis działania został opisany w pliku QoS_SDN_routing_RAPORT.pdf


