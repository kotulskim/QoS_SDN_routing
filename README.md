Uruchom maszynę wirtualną za pomocą obrazu .ova
Zaloguj się na konto student za pomocą hasła: @mininet
Przejdź do katalogu QoS_SDN_routing
Uruchom skrypty pytchona w osobnych oknach terminala za pomocą komend:

$ sudo python routing_net.py
$ sudo python ./pox.py routing_controller.py

W celu przetestwania działania routingu uruchom ping między hostami h1, h2, h3 a hostami h4, h5, h6:
mininet> h1 ping h5

Zaobserwuj działanie kontrollera SDN.

Pełny opis działania został opisany w pliku QoS_SDN_routing_RAPORT.pdf


