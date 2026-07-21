//Maya ASCII 2027 scene
//Name: dayz_skeleton.ma
//Last modified: Sun, Jul 19, 2026 05:08:45 AM
//Codeset: 1251
requires maya "2027";
requires "mtoa" "5.6.1.1";
currentUnit -l centimeter -a degree -t film;
fileInfo "application" "maya";
fileInfo "product" "Maya 2027";
fileInfo "version" "2027";
fileInfo "cutIdentifier" "202604221258-70da84b25e";
fileInfo "osv" "Windows 11 Pro v2009 (Build: 26200)";
fileInfo "UUID" "5D59CF7F-46CC-6165-7FE3-D6BF5AD9AF16";
createNode joint -n "Pelvis";
	rename -uid "669C3ABF-40E2-8991-D2D5-9C9867298BDC";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032useFBXASC032globalFBXASC032settings" 
		-ln "mrFBXASC032displacementFBXASC032useFBXASC032globalFBXASC032settings" -min 0 
		-max 1 -at "bool";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032viewFBXASC032dependent" 
		-ln "mrFBXASC032displacementFBXASC032viewFBXASC032dependent" -min 0 -max 1 -at "bool";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032method" -ln "mrFBXASC032displacementFBXASC032method" 
		-smn 0 -smx 100 -at "long";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032smoothingFBXASC032on" 
		-ln "mrFBXASC032displacementFBXASC032smoothingFBXASC032on" -min 0 -max 1 -at "bool";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032edgeFBXASC032length" 
		-ln "mrFBXASC032displacementFBXASC032edgeFBXASC032length" -smn 0 -smx 100 -at "double";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032maxFBXASC032displace" 
		-ln "mrFBXASC032displacementFBXASC032maxFBXASC032displace" -smn 0 -smx 100 -at "double";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032parametricFBXASC032subdivisionFBXASC032level" 
		-ln "mrFBXASC032displacementFBXASC032parametricFBXASC032subdivisionFBXASC032level" 
		-smn 0 -smx 100 -at "long";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 0 
		-smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".t" -type "double3" -0.013979153454833622 0.9996913570072089 -0.0013150046672418647 ;
	setAttr ".r" -type "double3" 90.000104957309418 -89.999997495521939 0 ;
	setAttr ".s" -type "double3" 0.0099999997764825821 0.0099999997764996535 0.0099999997764996518 ;
	setAttr ".jo" -type "double3" -90 0 0 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 90.000104957309418 -89.999997495521939 0 ;
	setAttr ".bps" -type "matrix" 4.3711387642779165e-10 0.0099999997764825717 7.9495204993262217e-19 0
		 -0.0099999997764828666 4.3711387642853787e-10 1.8318505824128499e-08 0 1.8318505824128476e-08 -8.0152227683591386e-16 0.0099999997764828735 0
		 -0.013979153454833622 0.9996913570072089 -0.0013150046672418647 1;
	setAttr ".radi" 0.027387927621603015;
	setAttr -k on ".mrFBXASC032displacementFBXASC032useFBXASC032globalFBXASC032settings" 
		yes;
	setAttr -k on ".mrFBXASC032displacementFBXASC032viewFBXASC032dependent" yes;
	setAttr -k on ".mrFBXASC032displacementFBXASC032method" 6;
	setAttr -k on ".mrFBXASC032displacementFBXASC032smoothingFBXASC032on" yes;
	setAttr -k on ".mrFBXASC032displacementFBXASC032edgeFBXASC032length" 2;
	setAttr -k on ".mrFBXASC032displacementFBXASC032maxFBXASC032displace" 20;
	setAttr -k on ".mrFBXASC032displacementFBXASC032parametricFBXASC032subdivisionFBXASC032level" 
		5;
	setAttr -k on ".MaxHandle" 2;
	setAttr ".fbxID" 5;
createNode joint -n "LeftUpLeg" -p "Pelvis";
	rename -uid "3546CF59-4107-F960-4283-66AD4F92AF4C";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" -7.9691661565042722 -11.697912273504587 0.13152042265233763 ;
	setAttr ".r" -type "double3" 0.00030059214175965574 1.1814654997771905 -175.77484953097715 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1.0000001192092896 1.0000003576278687 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 0.00030059214175965574 1.1814654997771905 -175.77484953097715 ;
	setAttr ".bps" -type "matrix" 0.00073660219241470683 -0.0099707013768504937 -0.00020619134930228557 0
		 0.0099728234039382652 0.00073675825379988639 3.4183354785281588e-08 0 1.5157239499795617e-05 -0.00020563357523367795 0.009997877382044832 0
		 0.10299996559135294 0.9199996921100938 -1.4758389673980715e-08 1;
	setAttr ".radi" 0.04514997884631157;
	setAttr -k on ".MaxHandle" 3;
	setAttr ".fbxID" 5;
createNode joint -n "LeftUpLegRoll" -p "LeftUpLeg";
	rename -uid "5AF0BE12-42E2-D0EB-CE0A-5C8213D3B666";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" 21.499992370605469 -1.71661376953125e-05 -0.00023508071899414062 ;
	setAttr ".r" -type "double3" -0.00020635968454491382 0.00036274681848953391 2.0063666336259177e-05 ;
	setAttr ".s" -type "double3" 1.0000005960464478 1.0000003576278687 1.0000005960464478 ;
	setAttr ".ssc" no;
	setAttr -av ".is" -type "double3" 0.99999994039535522 1.0000001192092896 1.0000003576278687 ;
	setAttr -av ".is";
	setAttr ".pa" -type "double3" -0.00020635968454491382 0.00036274681848953391 2.0063666336259177e-05 ;
	setAttr ".bps" -type "matrix" 0.00073660602774240126 -0.0099707057597622929 -0.00020625477004829491 0
		 0.009972826657883304 0.00073676274964127567 -1.7533521109213159e-09 0 1.5197830779358095e-05 -0.00020569417003753283 0.0099978820356780278 0
		 0.11883673235040587 0.70562972427141779 -0.0044354775040638429 1;
	setAttr ".radi" 0.043101259768009194;
	setAttr -k on ".MaxHandle" 4;
	setAttr ".fbxID" 5;
createNode joint -n "LeftKneeExtra" -p "LeftUpLegRoll";
	rename -uid "070B1136-455F-6E7F-EF0A-A9A723B5B084";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 3;
	setAttr ".t" -type "double3" 20.500026702880859 -5.7220458984375e-06 1.0000004768371582 ;
	setAttr ".r" -type "double3" 5.6392738952726644e-06 5.8842942521151294 -0.00016479286165094586 ;
	setAttr ".s" -type "double3" 0.99999994039535522 0.99999994039535522 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 5.6392738952726644e-06 5.8842942521151294 -0.00016479286165094586 ;
	setAttr ".bps" -type "matrix" 0.00073113816317904969 -0.0098970834604528782 -0.0012301494776761797 0
		 0.0099728281909454673 0.00073673390745368462 -1.369813047963465e-09 0 9.0630583254061562e-05 -0.0012268060863547018 0.0099240575528198004 0
		 0.13395231636168248 0.5010242914658124 0.0013341810053992794 1;
	setAttr ".radi" 0.043101259768009194;
	setAttr -k on ".MaxHandle" 5;
	setAttr ".fbxID" 5;
createNode joint -n "LeftLeg" -p "LeftUpLegRoll";
	rename -uid "6F6D07DB-49F7-35BA-C173-B99C3710E04A";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032useFBXASC032globalFBXASC032settings" 
		-ln "mrFBXASC032displacementFBXASC032useFBXASC032globalFBXASC032settings" -min 0 
		-max 1 -at "bool";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032viewFBXASC032dependent" 
		-ln "mrFBXASC032displacementFBXASC032viewFBXASC032dependent" -min 0 -max 1 -at "bool";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032method" -ln "mrFBXASC032displacementFBXASC032method" 
		-smn 0 -smx 100 -at "long";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032smoothingFBXASC032on" 
		-ln "mrFBXASC032displacementFBXASC032smoothingFBXASC032on" -min 0 -max 1 -at "bool";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032edgeFBXASC032length" 
		-ln "mrFBXASC032displacementFBXASC032edgeFBXASC032length" -smn 0 -smx 100 -at "double";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032maxFBXASC032displace" 
		-ln "mrFBXASC032displacementFBXASC032maxFBXASC032displace" -smn 0 -smx 100 -at "double";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032parametricFBXASC032subdivisionFBXASC032level" 
		-ln "mrFBXASC032displacementFBXASC032parametricFBXASC032subdivisionFBXASC032level" 
		-smn 0 -smx 100 -at "long";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 0 
		-smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 3;
	setAttr ".t" -type "double3" 20.500019073486328 -1.52587890625e-05 4.863739013671875e-05 ;
	setAttr ".r" -type "double3" -5.4152205736658165e-08 9.8071575440003045 -0.0002737934740627734 ;
	setAttr ".s" -type "double3" 1.0000001192092896 0.99999988079071045 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -5.4152205736658165e-08 9.8071575440003045 -0.0002737934740627734 ;
	setAttr ".bps" -type "matrix" 0.00072320617016719988 -0.0097899683389072803 -0.0019062061377990657 0
		 0.0099728289888592302 0.00073671501581903693 -2.7389603320585414e-09 0 0.00014043563998668318 -0.0019010250968159005 0.0098166473531464196 0
		 0.13393701853469459 0.50123004477363575 -0.0086632179531355609 1;
	setAttr ".radi" 0.046199984103441248;
	setAttr -k on ".mrFBXASC032displacementFBXASC032useFBXASC032globalFBXASC032settings" 
		yes;
	setAttr -k on ".mrFBXASC032displacementFBXASC032viewFBXASC032dependent" yes;
	setAttr -k on ".mrFBXASC032displacementFBXASC032method" 6;
	setAttr -k on ".mrFBXASC032displacementFBXASC032smoothingFBXASC032on" yes;
	setAttr -k on ".mrFBXASC032displacementFBXASC032edgeFBXASC032length" 2;
	setAttr -k on ".mrFBXASC032displacementFBXASC032maxFBXASC032displace" 20;
	setAttr -k on ".mrFBXASC032displacementFBXASC032parametricFBXASC032subdivisionFBXASC032level" 
		5;
	setAttr -k on ".MaxHandle" 6;
	setAttr ".fbxID" 5;
createNode joint -n "LeftLegRoll" -p "LeftLeg";
	rename -uid "12AD8BC7-464B-3AAF-D73C-72835D6709AD";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 4;
	setAttr ".t" -type "double3" 21.999979019165039 8.7738037109375e-05 1.9073486328125e-05 ;
	setAttr ".r" -type "double3" -1.2913331787417049e-05 -5.9764176610946437e-06 1.2806609273774285e-06 ;
	setAttr ".s" -type "double3" 0.99999964237213135 0.99999958276748657 0.99999982118606567 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -1.2913331787417049e-05 -5.9764176610946437e-06 1.2806609273774285e-06 ;
	setAttr ".bps" -type "matrix" 0.00072320614908719181 -0.0097899650195672205 -0.0019062044321305656 0
		 0.0099728247800541774 0.00073671535571331772 -4.908828808695519e-09 0 0.00014043778711586937 -0.0019010235696716444 0.0098166457966250027 0
		 0.14984841677994085 0.28585097509813878 -0.050599525753469862 1;
	setAttr ".radi" 0.038850034922361373;
	setAttr -k on ".MaxHandle" 7;
	setAttr ".fbxID" 5;
createNode joint -n "LeftFoot" -p "LeftLegRoll";
	rename -uid "AB6127B0-49FE-C974-EA24-8FB880963DC7";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 5;
	setAttr ".t" -type "double3" 18.500011444091797 7.05718994140625e-05 2.86102294921875e-05 ;
	setAttr ".r" -type "double3" 0.66948642695365046 -10.761425725644228 -4.2873076796106595 ;
	setAttr ".s" -type "double3" 0.99999964237213135 1.0000002384185791 1.0000005960464478 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 0.66948642695365046 -10.761425725644228 -4.2873076796106595 ;
	setAttr ".bps" -type "matrix" 2.2867432954616945e-06 -0.0099999394914341549 -3.4476098593267529e-05 0
		 0.0099999683633551079 2.3747124813423582e-06 -2.5666578232853683e-05 0 2.567463089067191e-05 -3.4470526680315666e-05 0.0099999210929710286 0
		 0.16322844663363603 0.10473650780156821 -0.085864048706521173 1;
	setAttr ".radi" 0.033502395004034041;
	setAttr -k on ".MaxHandle" 8;
	setAttr ".fbxID" 5;
createNode joint -n "LeftToeBase" -p "LeftFoot";
	rename -uid "35F30665-4E63-5E00-4637-EDB1A08BAFF0";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 6;
	setAttr ".t" -type "double3" 8.5001611709594727 1.33514404296875e-05 13.500433921813965 ;
	setAttr ".r" -type "double3" -0.0002733491436350555 -89.999954669997877 0 ;
	setAttr ".s" -type "double3" 1.0000008344650269 1 1.0000005960464478 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.0002733491436350555 -89.999954669997877 0 ;
	setAttr ".bps" -type "matrix" 2.5674654124421704e-05 -3.447846698135453e-05 0.0099999294102762655 0
		 0.0099999683741508975 2.3270043444830925e-06 -2.5666742750344788e-05 0 -2.2390160426018051e-06 0.0099999454358033757 3.4483908211101927e-05 0
		 0.16359463649199246 0.01927004338854349 0.048846172495213419 1;
	setAttr ".radi" 0.014168022349476816;
	setAttr -k on ".MaxHandle" 9;
	setAttr ".fbxID" 5;
createNode transform -n "LeftToeBase_End" -p "LeftToeBase";
	rename -uid "8E7303C5-4E44-39F1-D247-66BBF6817AAC";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" 6.7466626167297363 9.5367431640625e-06 -7.5101852416992188e-06 ;
	setAttr ".r" -type "double3" 0 6.3245883033105169e-05 0.00011592485641768985 ;
	setAttr ".s" -type "double3" 1.0000009536743164 1 1.0000005960464478 ;
	setAttr -k on ".MaxHandle" 10;
createNode locator -n "LeftToeBase_EndShape" -p "LeftToeBase_End";
	rename -uid "E7BACC4B-4E96-4864-E56A-DF83BBCC9557";
	setAttr -k off ".v";
createNode joint -n "RightUpLeg" -p "Pelvis";
	rename -uid "07990494-4E91-1BF7-F0FB-96A5D90D25AE";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" -7.9691661565042722 8.9020842932678743 0.13148039687281129 ;
	setAttr ".r" -type "double3" 179.99971814102926 -1.1814307642624853 -4.2250991575824326 ;
	setAttr ".s" -type "double3" 1.0000003576278687 0.99999988079071045 1.0000003576278687 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 179.99971814102926 -1.1814307642624853 -4.2250991575824326 ;
	setAttr ".bps" -type "matrix" 0.00073659520673181802 0.0099707062568807573 0.0002061826754496793 0
		 0.00997282146721086 -0.00073675210913738286 3.0914486740607384e-08 0 1.5221378181905217e-05 0.00020562005314996219 -0.0099978775627112548 0
		 -0.10299999547265269 0.91999970111463814 -3.7655018905258589e-08 1;
	setAttr ".radi" 0.045150078982114789;
	setAttr -k on ".MaxHandle" 11;
	setAttr ".fbxID" 5;
createNode joint -n "RightUpLegRoll" -p "RightUpLeg";
	rename -uid "4850214A-40B2-3B26-A726-68858C133B38";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" -21.500030517578125 7.62939453125e-06 0.00029516220092773438 ;
	setAttr ".r" -type "double3" 0.00019120527612052733 0.00025325057762614402 0.00021387027288970767 ;
	setAttr ".s" -type "double3" 1.0000001192092896 1 1 ;
	setAttr ".ssc" no;
	setAttr -av ".is" -type "double3" 1.0000003576278687 0.99999988079071045 1.0000003576278687 ;
	setAttr -av ".is";
	setAttr ".pa" -type "double3" 0.00019120527612052733 0.00025325057762614402 0.00021387027288970767 ;
	setAttr ".bps" -type "matrix" 0.00073663245320749343 0.0099707037863576466 0.00020622689132861164 0
		 0.0099728187683742024 -0.0007367886408521276 -3.2196698661846753e-09 0 1.5191353230756603e-05 0.00020566658300383815 -0.0099978766513194612 0
		 -0.11883673431712349 0.70562926738018961 -0.0044359224646930732 1;
	setAttr ".radi" 0.043101197183132184;
	setAttr -k on ".MaxHandle" 12;
	setAttr ".fbxID" 5;
createNode joint -n "RightKneeExtra" -p "RightUpLegRoll";
	rename -uid "2C93A21E-4756-DF25-A78D-AF87A4A11064";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 3;
	setAttr ".t" -type "double3" -20.499996185302734 3.814697265625e-06 -1.0000005960464478 ;
	setAttr ".r" -type "double3" -1.5228051450961127e-05 5.8843711340015759 -3.4331833834312714e-05 ;
	setAttr ".s" -type "double3" 1.0000003576278687 1 1.0000014305114746 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -1.5228051450961127e-05 5.8843711340015759 -3.4331833834312714e-05 ;
	setAttr ".bps" -type "matrix" 0.00073118788517559353 0.0098970851402021189 0.0012301350236210333 0
		 0.0099728191856769226 -0.00073678299242717067 -4.5848667690309062e-10 0 9.0633919907931077e-05 0.0012267930373107299 -0.0099240676007886896 0
		 -0.13395285011684832 0.50102420827885807 0.0013343096602695895 1;
	setAttr ".radi" 0.043101197183132184;
	setAttr -k on ".MaxHandle" 13;
	setAttr ".fbxID" 5;
createNode joint -n "RightLeg" -p "RightUpLegRoll";
	rename -uid "30D4D819-4B4E-F61A-1F25-0C967458D18A";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 3;
	setAttr ".t" -type "double3" -20.500011444091797 7.05718994140625e-05 -6.7234039306640625e-05 ;
	setAttr ".r" -type "double3" -2.7306242968314839e-05 9.8072733209298679 -5.6318271079845452e-05 ;
	setAttr ".s" -type "double3" 1.0000004768371582 1.0000003576278687 1.0000008344650269 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -2.7306242968314836e-05 9.8072733209298679 -5.6318271079845452e-05 ;
	setAttr ".bps" -type "matrix" 0.00072327058797839864 0.0097899679976310404 0.0019061982674541482 0
		 0.0099728229920591355 -0.00073678000974240082 1.6614926864872576e-09 0 0.00014044653747944335 0.0019010181181405707 -0.0098166511359581588 0
		 -0.13393700525857957 0.50122965982983947 -0.0086629038996045484 1;
	setAttr ".radi" 0.046200093626976024;
	setAttr -k on ".MaxHandle" 14;
	setAttr ".fbxID" 5;
createNode joint -n "RightLegRoll" -p "RightLeg";
	rename -uid "D875574E-49B6-DB3B-B802-F79A44D4AB45";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 4;
	setAttr ".t" -type "double3" -22.000026702880859 5.7220458984375e-05 2.09808349609375e-05 ;
	setAttr ".r" -type "double3" 8.5911003878224186e-06 -0.00016392454007916672 -0.00016648586101859224 ;
	setAttr ".s" -type "double3" 1 0.9999997615814209 1.0000001192092896 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 8.5911003878224186e-06 -0.00016392454007916672 -0.00016648586101859224 ;
	setAttr ".bps" -type "matrix" 0.00072324201149777455 0.0097899755772872556 0.0019061701817692873 0
		 0.0099728227369952575 -0.00073675110207516517 5.7284431900315165e-09 0 0.00014044298965493616 0.0019009904458899549 -0.0098166577598325973 0
		 -0.1498484039113181 0.2858501001876646 -0.050599522646023326 1;
	setAttr ".radi" 0.038850044310092924;
	setAttr -k on ".MaxHandle" 15;
	setAttr ".fbxID" 5;
createNode joint -n "RightFoot" -p "RightLegRoll";
	rename -uid "DF74F1DE-47E1-160C-784E-E0A9BFA671D1";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 5;
	setAttr ".t" -type "double3" -18.500001907348633 -1.1444091796875e-05 -0.000179290771484375 ;
	setAttr ".r" -type "double3" 0.66957679118492719 -10.76123526005718 -4.2875299706295174 ;
	setAttr ".s" -type "double3" 1.0000001192092896 0.99999958276748657 0.9999997615814209 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 0.66957679118492719 -10.76123526005718 -4.2875299706295174 ;
	setAttr ".bps" -type "matrix" 2.2844142752375926e-06 0.0099999509394691835 3.4472963027186877e-05 0
		 0.0099999624625981189 -2.3714448074831657e-06 2.5656361014012954e-05 0 2.5664487270780545e-05 3.4468698295614863e-05 -0.0099999180005799822 0
		 -0.16322852181353242 0.10473520093635744 -0.085861914608408627 1;
	setAttr ".radi" 0.033501831740140917;
	setAttr -k on ".MaxHandle" 16;
	setAttr ".fbxID" 5;
createNode joint -n "RightToeBase" -p "RightFoot";
	rename -uid "6C6D3767-423D-4612-D28D-FF9C23238AB0";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 6;
	setAttr ".t" -type "double3" -8.4999618530273438 2.47955322265625e-05 -13.500238418579102 ;
	setAttr ".r" -type "double3" -7.5038663596244285e-09 -89.999900068521967 0 ;
	setAttr ".s" -type "double3" 1.0000004768371582 0.9999997615814209 1.0000003576278687 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -7.5038663596244285e-09 -89.999900068521967 0 ;
	setAttr ".bps" -type "matrix" 2.5664503492847634e-05 3.4486155987445937e-05 -0.0099999227087717822 0
		 0.0099999600784212769 -2.3714442420866642e-06 2.5656354897059816e-05 0 -2.284370329900983e-06 -0.009999954455597088 -3.4490416552025095e-05 0
		 -0.16359416799038307 0.019270663714954325 0.048846344331133176 1;
	setAttr ".radi" 0.014167998880147935;
	setAttr -k on ".MaxHandle" 17;
	setAttr ".fbxID" 5;
createNode transform -n "RightToeBase_End" -p "RightToeBase";
	rename -uid "5BED1C2C-47CE-AF9C-98BC-96AB90533B5C";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" -6.7466573715209961 -1.33514404296875e-05 -3.8266181945800781e-05 ;
	setAttr ".r" -type "double3" -7.5038699378539029e-09 -0.00039921912570964314 0.00027492468893221126 ;
	setAttr ".s" -type "double3" 1.0000002384185791 1 1.0000002384185791 ;
	setAttr -k on ".MaxHandle" 18;
createNode locator -n "RightToeBase_EndShape" -p "RightToeBase_End";
	rename -uid "01B4C0FE-42EB-5721-8D83-ACB9F06E95BD";
	setAttr -k off ".v";
createNode joint -n "Spine" -p "Pelvis";
	rename -uid "A5B55C6E-47D5-CB48-D908-98B61F046C37";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" 3.0308872492574466 -1.3979152267992296 0.13150798383481674 ;
	setAttr ".r" -type "double3" 8.971456327499593e-05 3.0001312389265351 6.1150441348437774e-13 ;
	setAttr ".s" -type "double3" 1.0000003576278687 1 1.0000002384185791 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 8.971456327499593e-05 3.0001312389265351 6.1150441348437774e-13 ;
	setAttr ".bps" -type "matrix" -5.2224383333847422e-10 0.0099862974969035512 -0.00052338261202824967 0
		 -0.0099999997764419271 1.2566336747510482e-09 3.3955189815104913e-08 0 3.3974429436573121e-08 0.00052338254963406111 0.0099862963064038818 0
		 2.2345733128453782e-09 1.030000228211279 4.9533993794724507e-08 1;
	setAttr ".radi" 0.0062999939918518075;
	setAttr -k on ".MaxHandle" 19;
	setAttr ".fbxID" 5;
createNode joint -n "Spine1" -p "Spine";
	rename -uid "ED9BE80E-4108-34F4-ECF3-DC9AC3D54D4E";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" 2.995880126953125 -2.1118373751960462e-06 0.15701198577880859 ;
	setAttr ".r" -type "double3" -0.00024588686063993888 2.9999823431249428 2.5567108094579827e-07 ;
	setAttr ".s" -type "double3" 1.0000007152557373 1.0000002384185791 1.0000005960464478 ;
	setAttr ".ssc" no;
	setAttr -av ".is" -type "double3" 1.0000003576278687 1 1.0000002384185791 ;
	setAttr -av ".is";
	setAttr ".pa" -type "double3" -0.00024588686063993888 2.9999823431249428 2.5567108094579827e-07 ;
	setAttr ".bps" -type "matrix" -2.2996035663412137e-09 0.0099452273325460472 -0.0010453053837054496 0
		 -0.010000002160681063 -3.2293288458185831e-09 -8.7250708413439327e-09 0 -9.0148202295566098e-09 0.0010453052590880855 0.0099452249549032458 0
		 2.7122759302503345e-08 1.0600001557575314 2.6181397891041416e-08 1;
	setAttr ".radi" 0.016205207034945487;
	setAttr -k on ".MaxHandle" 20;
	setAttr ".fbxID" 5;
createNode joint -n "Spine2" -p "Spine1";
	rename -uid "5B81BFD3-49ED-AB12-7EEE-3DB5693F4918";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 3;
	setAttr ".t" -type "double3" 7.716705322265625 3.7485151551663876e-06 0.029631614685058594 ;
	setAttr ".r" -type "double3" 5.0020424865718879e-05 2.9998913343504658 -2.732075341869264e-05 ;
	setAttr ".s" -type "double3" 1.0000003576278687 1.0000001192092896 1.0000003576278687 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 5.0020424865718879e-05 2.9998913343504658 -2.732075341869264e-05 ;
	setAttr ".bps" -type "matrix" 2.9371685740626287e-09 0.0098768971929981512 -0.0015643475142759196 0
		 -0.010000003352778111 2.8786327806403308e-09 -6.007767417214944e-10 0 -1.430530366387298e-10 0.0015643475142634107 0.0098768948120951106 0
		 -2.8374887107489789e-08 1.1367755185283845 -0.0077715943626476477 1;
	setAttr ".radi" 0.021181424483656886;
	setAttr -k on ".MaxHandle" 21;
	setAttr ".fbxID" 5;
createNode joint -n "Spine3" -p "Spine2";
	rename -uid "A47BE006-4052-FA65-48F7-D39550F83A09";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 4;
	setAttr ".t" -type "double3" 10.064239501953125 2.2029995307093486e-05 -0.66784858703613281 ;
	setAttr ".r" -type "double3" -8.1962264347874603e-05 -9.0000018217522619 -5.4641526550027993e-05 ;
	setAttr ".s" -type "double3" 0.99999988079071045 1.0000001192092896 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -8.1962264347874603e-05 -9.0000018217522619 -5.4641526550027993e-05 ;
	setAttr ".bps" -type "matrix" 1.2297962659356072e-08 0.010000012873210225 -7.2634310241750932e-10 0
		 -0.010000004544850831 1.2297979192916366e-08 -1.6397787612124516e-08 0 -1.6397761326198207e-08 3.5389545916149345e-10 0.010000011713710314 0
		 -2.1901900828474385e-07 1.2351342301379156 -0.030111832655181005 1;
	setAttr ".radi" 0.053616063594818117;
	setAttr -k on ".MaxHandle" 22;
	setAttr ".fbxID" 5;
createNode joint -n "Neck" -p "Spine3";
	rename -uid "A34528B7-4B12-F42F-8BEF-87BC3A381829";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 5;
	setAttr ".t" -type "double3" 25.486663818359375 -1.2025979231111705e-05 1.511197566986084 ;
	setAttr ".r" -type "double3" -0.00027320745812990188 -10.000269534849828 5.4641523281481508e-05 ;
	setAttr ".s" -type "double3" 1.0000004768371582 0.99999970197677612 0.99999982118606567 ;
	setAttr ".ssc" no;
	setAttr -av ".is" -type "double3" 0.99999988079071045 1.0000001192092896 1 ;
	setAttr -av ".is";
	setAttr ".pa" -type "double3" -0.00027320745812990188 -10.000269534849828 5.4641523281481508e-05 ;
	setAttr ".bps" -type "matrix" -1.2825526348420727e-10 0.0098480867961531927 0.0017365302515088144 0
		 -0.010000001564431444 1.1041635699456481e-08 -6.3357059046380644e-08 0 -6.4311828588134427e-08 -0.0017365296810744786 0.0098480792618461169 0
		 1.898946216122307e-07 1.4900011969513487 -0.014999857795454905 1;
	setAttr ".radi" 0.016062192767858509;
	setAttr -k on ".MaxHandle" 23;
	setAttr ".fbxID" 5;
createNode joint -n "Neck1" -p "Neck";
	rename -uid "F36B557C-4E1F-0A5D-DA7C-C98E31B67641";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 6;
	setAttr ".t" -type "double3" 7.6466522216796875 9.6737785497680306e-06 0.17485427856445312 ;
	setAttr ".r" -type "double3" 0.00021856594746726845 10.000027684349408 1.322852167498902e-11 ;
	setAttr ".s" -type "double3" 1.0000001192092896 0.99999994039535522 1.0000001192092896 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 0.00021856594746726845 10.000027684349408 1.322852167498902e-11 ;
	setAttr ".bps" -type "matrix" 1.1041356988201305e-08 0.010000018635887764 4.2605856756484581e-08 0
		 -0.010000000968553833 1.1041479646730771e-08 -2.52100647667481e-08 0 -2.5210096238410098e-08 -4.0735808265858833e-08 0.010000011315267586 0
		 8.0930899194184397e-08 1.5650024520859647 7.6390422170877215e-07 1;
	setAttr ".radi" 0.011550064086914065;
	setAttr -k on ".MaxHandle" 24;
	setAttr ".fbxID" 5;
createNode joint -n "Head" -p "Neck1";
	rename -uid "8D794C7B-46EC-400F-94D4-1BA8AE1016D3";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 7;
	setAttr ".t" -type "double3" 5.5000152587890625 5.5569398682564497e-07 2.2507738322019577e-05 ;
	setAttr ".r" -type "double3" 0.00032784902804700283 6.5474099990803483e-05 -2.7320727368053493e-05 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 0.99999994039535522 ;
	setAttr ".ssc" no;
	setAttr -av ".is" -type "double3" 1.0000001192092896 0.99999994039535522 1.0000001192092896 ;
	setAttr -av ".is";
	setAttr ".pa" -type "double3" 0.00032784902804700283 6.5474099990803483e-05 -2.7320727368053493e-05 ;
	setAttr ".bps" -type "matrix" 1.580975178236997e-08 0.010000018039873824 3.1178467792567183e-08 0
		 -0.010000000968527975 1.5809687294879545e-08 3.2010470184934845e-08 0 3.201037535102806e-08 -2.9308489490997842e-08 0.010000010719243167 0
		 1.3610102327830362e-07 1.6200027071706116 1.2233147078754146e-06 1;
	setAttr ".radi" 0.013424434214830399;
	setAttr -k on ".MaxHandle" 25;
	setAttr ".fbxID" 5;
createNode transform -n "Camera1st_lock_dummy" -p "Head";
	rename -uid "62D4B385-4D72-BC6A-45A2-678BC37FDA0A";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 5.209991455078125 -2.830000638961792 2.3899998664855957 ;
	setAttr ".r" -type "double3" -137.06290631362418 -89.999749787435505 47.063014398646416 ;
	setAttr ".s" -type "double3" 0.99999958276748657 1.0000003576278687 1.0000001192092896 ;
	setAttr -k on ".MaxHandle" 26;
createNode locator -n "Camera1st_lock_dummyShape" -p "Camera1st_lock_dummy";
	rename -uid "98A302D8-424D-B009-E1A7-9280E204CE40";
	setAttr -k off ".v";
createNode transform -n "Face_Hub" -p "Head";
	rename -uid "DFE5823D-477F-590D-2BB3-2CAD8D9DCACF";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 4.1999969482421875 2.0262712496332824e-05 3.2412935979664326e-07 ;
	setAttr ".r" -type "double3" -0.00018835667520940866 0.00033661395512219052 -7.864552902946355e-05 ;
	setAttr ".s" -type "double3" 0.99999958276748657 1.0000001192092896 0.99999994039535522 ;
	setAttr -k on ".MaxHandle" 27;
createNode locator -n "Face_HubShape" -p "Face_Hub";
	rename -uid "1EC11DEB-473B-7834-27D7-F69790650F11";
	setAttr -k off ".v";
createNode joint -n "Face_EyelidUpperLeft" -p "Face_Hub";
	rename -uid "C9DD4EF3-440E-B63E-7525-10B44E2D339B";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" -1.2491912841796875 -3.5003602504730225 -4.3900594711303711 ;
	setAttr ".r" -type "double3" -8.1962263526321112e-05 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -8.1962263526321112e-05 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000002160629592 2.9535810907537827e-08 -1.5169091956637304e-08 0 -1.5169012462623994e-08 2.9441972338148219e-08 0.010000010123246405 0
		 0.035003576839256742 1.6495105896178404 -0.043899244180190339 1;
	setAttr ".radi" 0.012079231739044191;
	setAttr -k on ".MaxHandle" 28;
	setAttr ".fbxID" 5;
createNode joint -n "Face_EyelidUpperRight" -p "Face_Hub";
	rename -uid "563559AD-41A4-D269-E70D-348981D26FB6";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" -1.2492523193359375 3.4996569156646729 -4.3900542259216309 ;
	setAttr ".r" -type "double3" -8.1962263526321112e-05 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -8.1962263526321112e-05 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000002160629592 2.9535810907537827e-08 -1.5169091956637304e-08 0 -1.5169012462623994e-08 2.9441972338148219e-08 0.010000010123246405 0
		 -0.034996609948451975 1.649510186017064 -0.04389919777412888 1;
	setAttr ".radi" 0.012078350856900216;
	setAttr -k on ".MaxHandle" 29;
	setAttr ".fbxID" 5;
createNode joint -n "Face_Jawbone" -p "Face_Hub";
	rename -uid "A688B313-43F0-4B63-FA72-F28033032EA4";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" -3.7103118896484375 5.1449082093313336e-05 2.0434916019439697 ;
	setAttr ".r" -type "double3" 1.4864123519152154e-13 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 1.4864123519152154e-13 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000002160641059 2.9535853024583527e-08 -8.639638659920577e-10 0 -8.6389576259256025e-10 2.9441930086805039e-08 0.010000010123257871 0
		 -6.2596847906211369e-07 1.6248996422373454 0.02043639651245838 1;
	setAttr ".radi" 0.0030157195776700976;
	setAttr -k on ".MaxHandle" 30;
	setAttr ".fbxID" 5;
createNode joint -n "Face_Chin" -p "Face_Jawbone";
	rename -uid "9F93C0A1-4A29-031D-0992-19ABB9BDF315";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" 0.96173095703125 -0.00040366148459725082 1.0664365291595459 ;
	setAttr ".r" -type "double3" 6.8340046138333312e-06 0.0013079811212672052 -0.0013113960077522011 ;
	setAttr ".s" -type "double3" 1 1.0000001192092896 0.99999970197677612 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 6.8340046138333312e-06 0.0013079811212672052 -0.0013113960077522011 ;
	setAttr ".bps" -type "matrix" 2.5841763560865623e-07 0.010000013264889166 -2.5585782671609109e-07 0
		 -0.010000003349438878 2.5841799963086342e-07 3.281651272259449e-10 0 3.3476251773805853e-10 2.5772789652112761e-07 0.010000007139787499 0
		 3.4381314280475908e-06 1.6345169959572614 0.031100746083518441 1;
	setAttr ".radi" 0.0030157195776700976;
	setAttr -k on ".MaxHandle" 31;
	setAttr ".fbxID" 5;
createNode joint -n "Face_ChopLeft" -p "Face_Jawbone";
	rename -uid "55F4FC1C-466A-BDC1-523B-E394EDD3F34A";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" -5.0381927490234375 -5.00006103515625 15.566444396972656 ;
	setAttr ".r" -type "double3" -2.2940741828644036e-12 -3.9082655925823694e-11 -2.6055103950549129e-11 ;
	setAttr ".s" -type "double3" 1 1.0000001192092896 0.99999970197677612 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -2.2940741828644036e-12 -3.9082655925823694e-11 -2.6055103950549129e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000003352734212 2.9535856545531581e-08 -8.6396396898457633e-10 0 -8.6389550513155999e-10 2.9441921312426119e-08 0.010000007143022615 0
		 0.04999983293165642 1.5745179585080253 0.17610114129745341 1;
	setAttr ".radi" 0.035927718579769147;
	setAttr -k on ".MaxHandle" 32;
	setAttr ".fbxID" 5;
createNode joint -n "Face_ChopRight" -p "Face_Jawbone";
	rename -uid "CE04C31B-440E-C010-DF69-9BABFAF16E57";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" -5.0381011962890625 4.9996089935302734 15.566429138183594 ;
	setAttr ".r" -type "double3" -2.2940741828644036e-12 -3.9082655925823694e-11 -2.6055103950549129e-11 ;
	setAttr ".s" -type "double3" 1 1.0000001192092896 0.99999970197677612 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -2.2940741828644036e-12 -3.9082655925823694e-11 -2.6055103950549129e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000003352734212 2.9535856545531581e-08 -8.6396396898457633e-10 0 -8.6389550513155999e-10 2.9441921312426119e-08 0.010000007143022615 0
		 -0.049996888958189198 1.5745191693849192 0.17610098006753047 1;
	setAttr ".radi" 0.035927358716726303;
	setAttr -k on ".MaxHandle" 33;
	setAttr ".fbxID" 5;
createNode joint -n "Face_Jowl" -p "Face_Jawbone";
	rename -uid "FABBC0FE-466B-BD47-943E-FCA782E11FC4";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" -16.277862548828125 -8.8206958025693893e-05 3.4305112361907959 ;
	setAttr ".r" -type "double3" 6.8301549726888436e-06 -1.0245335865226846e-05 6.8301631149087682e-06 ;
	setAttr ".s" -type "double3" 1 1 0.99999970197677612 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 6.8301549726888436e-06 -1.0245335865226846e-05 6.8301631149087682e-06 ;
	setAttr ".bps" -type "matrix" 2.8343696441134889e-08 0.010000013271470931 -2.5783694079506165e-08 0
		 -0.01000000216064454 2.8343766391044129e-08 3.2812755454511751e-10 0 3.2818625584306594e-10 2.7653767655170197e-08 0.010000007143027416 0
		 -2.2764176411915629e-07 1.4621209017162904 0.054741992413082932 1;
	setAttr ".radi" 0.0349344027042389;
	setAttr -k on ".MaxHandle" 34;
	setAttr ".fbxID" 5;
createNode joint -n "Face_LipLowerLeft" -p "Face_Jawbone";
	rename -uid "A870A44A-4CD0-EA5A-7EA9-D4964A1E4B97";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" -2.2721710205078125 -1.5004082918167114 7.9711389541625977 ;
	setAttr ".r" -type "double3" -0.00013660374431734024 -3.9082655925823694e-11 -2.6055103950549129e-11 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.00013660374431734024 -3.9082655925823694e-11 -2.6055103950549129e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000002160610578 2.9535782829488292e-08 -2.4705839090588497e-08 0 -2.4705752002836568e-08 2.9442000505662321e-08 0.01000001012322739 0
		 0.015003386194943446 1.6021780922471121 0.1001479306922235 1;
	setAttr ".radi" 0.017689069435000419;
	setAttr -k on ".MaxHandle" 35;
	setAttr ".fbxID" 5;
createNode joint -n "Face_LipLowerMiddle" -p "Face_Jawbone";
	rename -uid "37AF381F-4548-120F-60DD-C2B08427F0F6";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" -2.03814697265625 -0.00040595384780317545 8.5664310455322266 ;
	setAttr ".r" -type "double3" -0.032836123371179561 0.0020712545236062385 -0.0020763763342949442 ;
	setAttr ".s" -type "double3" 0.9999997615814209 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.032836123371179561 0.0020712545236062385 -0.0020763763342949442 ;
	setAttr ".bps" -type "matrix" 3.9193183637270925e-07 0.010000010872037975 -3.8907419683326988e-07 0
		 -0.0100000005103076 3.9170825526149456e-07 -5.7318551106889378e-06 0 -5.7318353115504933e-06 3.9116907194270505e-07 0.010000008473020362 0
		 3.3659721014165343e-06 1.6045183976618658 0.10610084988379272 1;
	setAttr ".radi" 0.018491678237915039;
	setAttr -k on ".MaxHandle" 36;
	setAttr ".fbxID" 5;
createNode joint -n "Face_LipLowerRight" -p "Face_Jawbone";
	rename -uid "E2A790F1-4955-CD65-BAD0-198E984D924D";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" -2.27203369140625 1.4995990991592407 7.971135139465332 ;
	setAttr ".r" -type "double3" -0.00021856601435669658 -3.9082655925823694e-11 -2.6055103950549129e-11 ;
	setAttr ".s" -type "double3" 1 1.0000001192092896 0.99999970197677612 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.00021856601435669658 -3.9082655925823694e-11 -2.6055103950549129e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000003352658157 2.9535744233273176e-08 -3.9010972968375799e-08 0 -3.9010858213394141e-08 2.9442033982495943e-08 0.010000007142946559 0
		 -0.014996694192695803 1.6021795541476154 0.10014788994952782 1;
	setAttr ".radi" 0.017688690796494488;
	setAttr -k on ".MaxHandle" 37;
	setAttr ".fbxID" 5;
createNode joint -n "Face_Tongue" -p "Face_Jawbone";
	rename -uid "8ACD4081-4C87-2DD5-7E7F-B69E84EA1E14";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" -1.4859619140625 -0.00040790275670588017 11.440195083618164 ;
	setAttr ".r" -type "double3" -0.00035516978472590585 -3.9082655925823694e-11 -2.6055103950549129e-11 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.00035516978472590585 -3.9082655925823694e-11 -2.6055103950549129e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000002160443573 2.9535670516961262e-08 -6.2852848089126188e-08 0 -6.2852730626403483e-08 2.944211317551138e-08 0.010000010123060385 0
		 3.3992877813612268e-06 1.6100403401852088 0.13483850413174778 1;
	setAttr ".radi" 0.024226244464516641;
	setAttr -k on ".MaxHandle" 38;
	setAttr ".fbxID" 5;
createNode joint -n "EyeRight" -p "Face_Hub";
	rename -uid "9F658D81-496E-9C15-B079-3FBC0FCDD3C6";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" 2.150054931640625 3.2999663352966309 8.3500099182128906 ;
	setAttr ".r" -type "double3" 1.4864123519152154e-13 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 1.4864123519152154e-13 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000002160641059 2.9535853024583527e-08 -8.639638659920577e-10 0 -8.6389576259256025e-10 2.9441930086805039e-08 0.010000010123257871 0
		 -0.032999614318184531 1.6835036748608019 0.08350147908552083 1;
	setAttr ".radi" 0.019387829527258874;
	setAttr -k on ".MaxHandle" 39;
	setAttr ".fbxID" 5;
createNode joint -n "EyeLeft" -p "Face_Hub";
	rename -uid "DB32DE08-44CE-33FB-FC29-AEB066625032";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" 2.1499786376953125 -3.300037145614624 8.3498506546020508 ;
	setAttr ".r" -type "double3" 1.4864123519152154e-13 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 1.4864123519152154e-13 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000002160641059 2.9535853024583527e-08 -8.639638659920577e-10 0 -8.6389576259256025e-10 2.9441930086805039e-08 0.010000010123257871 0
		 0.033000434749050712 1.683502716978869 0.083499892152068253 1;
	setAttr ".radi" 0.019387541636824608;
	setAttr -k on ".MaxHandle" 40;
	setAttr ".fbxID" 5;
createNode joint -n "Face_CheekFrontLeft" -p "Face_Hub";
	rename -uid "129C47D0-4E9C-AC55-00EA-4AA1F73B5795";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" -6.7491912841796875 6.9996623992919922 14.209577560424805 ;
	setAttr ".r" -type "double3" -6.8302005691193504e-06 -3.4151210472244759e-06 -2.605510705655993e-11 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1.0000001192092896 0.99999970197677612 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -6.8302005691193504e-06 -3.4151210472244759e-06 -2.605510705655993e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785149722091e-08 0.010000013271464114 -2.6975792590759443e-08 0
		 -0.010000003352734039 2.9535853106828576e-08 -2.0560602029093138e-09 0 -2.0559920529388659e-09 2.884587311815942e-08 0.010000007143024067 0
		 -0.069996850860149382 1.594511371082876 0.14209745699779552 1;
	setAttr ".radi" 0.036157796233892453;
	setAttr -k on ".MaxHandle" 41;
	setAttr ".fbxID" 5;
createNode joint -n "Face_CheekFrontRight" -p "Face_Hub";
	rename -uid "2E06A98C-4DED-F0FF-6904-91ABDA1226BF";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" -6.7492218017578125 -7.000363826751709 14.209565162658691 ;
	setAttr ".r" -type "double3" -0.00021856601435669192 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.00021856601435669192 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000002160565003 2.9535740712338513e-08 -3.9010968317905164e-08 0 -3.9010869839538518e-08 2.9442042756908446e-08 0.010000010123181816 0
		 0.070003441648428477 1.5945106524035897 0.14209734511636707 1;
	setAttr ".radi" 0.036158400177955637;
	setAttr -k on ".MaxHandle" 42;
	setAttr ".fbxID" 5;
createNode joint -n "Face_CheekUpperLeft" -p "Face_Hub";
	rename -uid "88F2AB47-4D3D-AFF1-5C8A-13AAFA33F549";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" 6.250701904296875 10.999668121337891 3.109938383102417 ;
	setAttr ".r" -type "double3" -0.00019124524464943888 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.00019124524464943888 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000002160582468 2.953575475140185e-08 -3.424258963508243e-08 0 -3.4242494953589164e-08 2.9442028673159714e-08 0.010000010123199281 0
		 -0.10999652317217795 1.7245102745925665 0.031100590973150263 1;
	setAttr ".radi" 0.027359370142221461;
	setAttr -k on ".MaxHandle" 43;
	setAttr ".fbxID" 5;
createNode joint -n "Face_CheekUpperRight" -p "Face_Hub";
	rename -uid "50E749CB-415C-BEF4-6215-0195FCC17DBE";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" 6.2507171630859375 -11.000387191772461 3.1099400520324707 ;
	setAttr ".r" -type "double3" 6.8297564110259385e-06 -0.00016050950371125663 0.00014343391150331097 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 6.8297564110259385e-06 -0.00016050950371125663 0.00014343391150331097 ;
	setAttr ".bps" -type "matrix" 4.501838716730614e-09 0.010000013271548218 4.4237350715127736e-10 0
		 -0.010000002160683695 4.5018783313910622e-09 3.2812372873495988e-10 0 3.2810924823852528e-10 1.4276974962307753e-09 0.010000010123295903 0
		 0.1100040774935976 1.7245097773903175 0.031100626669299823 1;
	setAttr ".radi" 0.027360662519931793;
	setAttr -k on ".MaxHandle" 44;
	setAttr ".fbxID" 5;
createNode joint -n "Face_CornerLeft" -p "Face_Hub";
	rename -uid "697A87FC-4DBE-2BD3-F36D-70AEAD94EACA";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" -5.749176025390625 15.499669075012207 -4.3900661468505859 ;
	setAttr ".r" -type "double3" -0.00054641492514362301 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.00054641492514362301 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000002160178073 2.953557224322202e-08 -9.6231455665326347e-08 0 -9.623131162452438e-08 2.9442211761203136e-08 0.010000010122794884 0
		 -0.1549968903784239 1.6045112409840261 -0.04389920327991316 1;
	setAttr ".radi" 0.0041999709606170658;
	setAttr -k on ".MaxHandle" 45;
	setAttr ".fbxID" 5;
createNode joint -n "Face_CheekSideLeft" -p "Face_CornerLeft";
	rename -uid "BBBA7740-4D3F-44A9-1DDE-8CBEDCCF9975";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" 1.9999847412109375 0 7.62939453125e-06 ;
	setAttr ".r" -type "double3" -0.00035516982055167572 -2.6055110162571473e-11 3.9082665243857209e-11 ;
	setAttr ".s" -type "double3" 0.9999997615814209 1.0000001192092896 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.00035516982055167572 -2.6055110162571473e-11 3.9082665243857209e-11 ;
	setAttr ".bps" -type "matrix" 2.9535778159334795e-08 0.01000001088727342 -2.7571837651272223e-08 0
		 -0.010000003351482569 2.9535393254728111e-08 -1.5822036499787596e-07 0 -1.5822015273641078e-07 2.944239484818741e-08 0.010000010122006225 0
		 -0.15499683130803837 1.6245111149390823 -0.043899182129158353 1;
	setAttr ".radi" 0.0041999709606170658;
	setAttr -k on ".MaxHandle" 46;
	setAttr ".fbxID" 5;
createNode joint -n "Face_CornerRight" -p "Face_Hub";
	rename -uid "2DBA40D7-4E87-84C7-9415-1E9905CB181B";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" -5.7491455078125 -15.500395774841309 -4.390070915222168 ;
	setAttr ".r" -type "double3" 6.8297393123642143e-06 -0.0001673397197504701 0.00015026411451505447 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 6.8297393123642143e-06 -0.0001673397197504701 0.00015026411451505447 ;
	setAttr ".bps" -type "matrix" 3.3097431158841127e-09 0.010000013271548784 1.6344721249760203e-09 0
		 -0.01000000216068416 3.3097812248007058e-09 3.2812403127955883e-10 0 3.281092089643397e-10 2.3559840010971124e-10 0.01000001012329578 0
		 0.15500382510102967 1.6045106305467312 -0.043899224181582812 1;
	setAttr ".radi" 0.0042000460624694825;
	setAttr -k on ".MaxHandle" 47;
	setAttr ".fbxID" 5;
createNode joint -n "Face_CheekSideRight" -p "Face_CornerRight";
	rename -uid "867711DD-4F43-20B4-E2F1-B688BE08D15A";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" 2.0000152587890625 6.67572021484375e-06 5.7220458984375e-06 ;
	setAttr ".r" -type "double3" -0.00027320753422956329 -3.2568879938186412e-12 -1.6284439969093206e-12 ;
	setAttr ".s" -type "double3" 1 1.0000001192092896 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.00027320753422956329 -3.2568879938186412e-12 -1.6284439969093206e-12 ;
	setAttr ".bps" -type "matrix" 3.3097431158841127e-09 0.010000013271548784 1.6344721249760203e-09 0
		 -0.010000003352665191 3.3097804958990307e-09 -4.7355640021015055e-08 0 -4.7355611229412292e-08 2.3561418237188626e-10 0.010000010123183658 0
		 0.15500376496335172 1.6245108096779453 -0.043899163692094519 1;
	setAttr ".radi" 0.0042000460624694825;
	setAttr -k on ".MaxHandle" 48;
	setAttr ".fbxID" 5;
createNode joint -n "Face_EyelidLowerLeft" -p "Face_Hub";
	rename -uid "61369FBA-43FA-E588-A073-2BA98E91E42F";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" 4.2507476806640625 -1.0003535747528076 -4.3900542259216309 ;
	setAttr ".r" -type "double3" 1.4864123519152154e-13 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 1.4864123519152154e-13 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000002160641059 2.9535853024583527e-08 -8.639638659920577e-10 0 -8.6389576259256025e-10 2.9441930086805039e-08 0.010000010123257871 0
		 0.010003667125458554 1.7045101293767186 -0.043899345531434701 1;
	setAttr ".radi" 0.013003435917198658;
	setAttr -k on ".MaxHandle" 49;
	setAttr ".fbxID" 5;
createNode joint -n "Face_EyelidLowerRight" -p "Face_Hub";
	rename -uid "73FF98BC-42CB-A996-9456-0FAECB26845B";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" 4.25079345703125 0.99964946508407593 -4.3900575637817383 ;
	setAttr ".r" -type "double3" 1.4864123519152154e-13 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 1.4864123519152154e-13 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000002160641059 2.9535853024583527e-08 -8.639638659920577e-10 0 -8.6389576259256025e-10 2.9441930086805039e-08 0.010000010123257871 0
		 -0.009996367592844042 1.7045106462127229 -0.043899380639262055 1;
	setAttr ".radi" 0.013003262244164947;
	setAttr -k on ".MaxHandle" 50;
	setAttr ".fbxID" 5;
createNode joint -n "Face_Eyelids" -p "Face_Hub";
	rename -uid "6B4BE4C1-41A7-E424-49F8-93965884D5E4";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" 1.750762939453125 -0.00034976456663571298 -10.390055656433105 ;
	setAttr ".r" -type "double3" -6.8302005691193504e-06 -3.4151210472244759e-06 -2.605510705655993e-11 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1.0000001192092896 0.99999970197677612 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -6.8302005691193504e-06 -3.4151210472244759e-06 -2.605510705655993e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785149722091e-08 0.010000013271464114 -2.6975792590759443e-08 0
		 -0.010000003352734039 2.9535853106828576e-08 -2.0560602029093138e-09 0 -2.0559920529388659e-09 2.884587311815942e-08 0.010000007143024067 0
		 3.5582073066315017e-06 1.6795101001803896 -0.10389935251088434 1;
	setAttr ".radi" 0.02212673150002957;
	setAttr -k on ".MaxHandle" 51;
	setAttr ".fbxID" 5;
createNode joint -n "Face_Forehead" -p "Face_Hub";
	rename -uid "348A0DA3-42C3-7813-3BF9-DDB277CA3D50";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" 6.250732421875 -0.00035132508492097259 -0.39005962014198303 ;
	setAttr ".r" -type "double3" -0.00084694314435864631 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.00084694314435864631 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.01000000215953576 2.9535417812322847e-08 -1.4868357796449028e-07 0 -1.4868339215811551e-07 2.9442366680986058e-08 0.010000010122152569 0
		 3.6980836786210188e-06 1.7245101518271166 -0.0038994149878981716 1;
	setAttr ".radi" 0.017189199328422552;
	setAttr -k on ".MaxHandle" 52;
	setAttr ".fbxID" 5;
createNode joint -n "Face_BrowFrontLeft" -p "Face_Forehead";
	rename -uid "58753FE5-45B9-4B9C-86BE-FBA0D959FAEC";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" -2.9999542236328125 6.9999980926513672 2.9999935626983643 ;
	setAttr ".r" -type "double3" 0.057093523488360005 -0.010107116420393482 0.0095416257724292037 ;
	setAttr ".s" -type "double3" 1 1.0000025033950806 1.0000038146972656 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 0.057093523488360005 -0.010107116420393482 0.0095416257724292037 ;
	setAttr ".bps" -type "matrix" -1.6358186270295098e-06 0.010000012987319328 1.7364297665027985e-06 0
		 -0.010000022242840788 -1.6375263905945902e-06 9.8160536144452374e-06 0 9.8163427217923661e-06 -1.7329602658872494e-06 0.010000043301811312 0
		 -0.069996832614804175 1.6945108648517877 0.026099592934986392 1;
	setAttr ".radi" 0.017189199328422552;
	setAttr -k on ".MaxHandle" 53;
	setAttr ".fbxID" 5;
createNode joint -n "Face_BrowFrontRight" -p "Face_Forehead";
	rename -uid "46713A12-4E0D-526B-464C-82A76FDC54D7";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" -2.9999542236328125 -7.0000333786010742 2.9999809265136719 ;
	setAttr ".r" -type "double3" 0.060501781294301345 -0.011551713324154979 0.010525147953625174 ;
	setAttr ".s" -type "double3" 1.0000004768371582 1.0000017881393433 1.0000029802322388 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 0.060501781294301345 -0.011551713324154979 0.010525147953625174 ;
	setAttr ".bps" -type "matrix" -1.8074802641761884e-06 0.010000017679231692 1.9885581367243166e-06 0
		 -0.010000014459032796 -1.8095519802135238e-06 1.0410901574929408e-05 0 1.0411265145767552e-05 -1.9848108001369765e-06 0.010000034308593661 0
		 0.070003512333167636 1.694510451354637 0.02610154814778233 1;
	setAttr ".radi" 0.017189261913299562;
	setAttr -k on ".MaxHandle" 54;
	setAttr ".fbxID" 5;
createNode joint -n "Face_BrowMiddle" -p "Face_Forehead";
	rename -uid "0272CF07-403E-F4EA-71E1-108D12EA5CE9";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" -10.999893188476562 -3.6321289371699095e-06 6.9999914169311523 ;
	setAttr ".r" -type "double3" -0.00019124528698898397 -3.9082665243857209e-11 -1.3027555081285736e-11 ;
	setAttr ".s" -type "double3" 0.9999997615814209 1.0000001192092896 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.00019124528698898397 -3.9082665243857209e-11 -1.3027555081285736e-11 ;
	setAttr ".bps" -type "matrix" 2.9535778159334795e-08 0.01000001088727342 -2.7571837651272223e-08 0
		 -0.010000003351076923 2.9535323058546586e-08 -1.8206223282222682e-07 0 -1.8206199873424559e-07 2.944246526590988e-08 0.010000010121600577 0
		 2.3687320244382642e-06 1.6145112800538892 0.066100873324275972 1;
	setAttr ".radi" 0.027380495667457583;
	setAttr -k on ".MaxHandle" 55;
	setAttr ".fbxID" 5;
createNode joint -n "Face_BrowSideLeft" -p "Face_Forehead";
	rename -uid "0DE45AD7-4478-5BA4-DED2-C1AD67515853";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" 2.0000152587890625 -9.0000362396240234 14.999994277954102 ;
	setAttr ".r" -type "double3" -8.1962478482767661e-05 -5.1226089012277035e-06 -3.4151637944867709e-06 ;
	setAttr ".s" -type "double3" 0.99999117851257324 0.99999117851257324 0.99999117851257324 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -8.1962478482767661e-05 -5.1226089012277035e-06 -3.4151637944867709e-06 ;
	setAttr ".bps" -type "matrix" 3.0131564756212455e-08 0.0099999250564718461 -2.6677535203714074e-08 0
		 -0.0099999139444177394 3.0131170487572521e-08 -1.6298730741069838e-07 0 -1.6298711126594006e-07 2.8548092842889141e-08 0.0099999219069685091 0
		 0.090001908737808431 1.7445105067736355 0.14610196263735423 1;
	setAttr ".radi" 0.036974375545978544;
	setAttr -k on ".MaxHandle" 56;
	setAttr ".fbxID" 5;
createNode joint -n "Face_BrowSideRight" -p "Face_Forehead";
	rename -uid "654CC81A-46AD-018B-E6FF-9799D2599951";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" 1.999969482421875 9.0000104904174805 14.999980926513672 ;
	setAttr ".r" -type "double3" 0.00087426390103303151 -0.00017417230151220786 0.00016392189548617729 ;
	setAttr ".s" -type "double3" 0.9999997615814209 1.0000001192092896 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 0.00087426390103303151 -0.00017417230151220786 0.00016392189548617729 ;
	setAttr ".bps" -type "matrix" 9.2555889894911461e-10 0.010000010887360291 2.8265617628840076e-09 0
		 -0.010000003352777063 9.2559743504488338e-10 3.9044918912362756e-09 0 3.9044740351128561e-09 -9.5648905813424266e-10 0.010000010123294756 0
		 -0.089998597433718117 1.744510580647864 0.14609915281272559 1;
	setAttr ".radi" 0.036974319219589241;
	setAttr -k on ".MaxHandle" 57;
	setAttr ".fbxID" 5;
createNode joint -n "Face_LipUpperLeft" -p "Face_Hub";
	rename -uid "AD78D135-43DC-E516-52DC-F59A903A507A";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" -4.891021728515625 -1.5003582239151001 10.179598808288574 ;
	setAttr ".r" -type "double3" -0.00043713208081723064 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.00043713208081723064 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.01000000216034343 2.9535628399636922e-08 -7.7157981863096589e-08 0 -7.7157853009755561e-08 2.9442155426610271e-08 0.010000010122960241 0
		 0.015003432101396812 1.6130927227019884 0.10179758479046519 1;
	setAttr ".radi" 0.023925042226910592;
	setAttr -k on ".MaxHandle" 58;
	setAttr ".fbxID" 5;
createNode joint -n "Face_LipUpperMiddle" -p "Face_Hub";
	rename -uid "155DBFCB-424C-654F-F095-559CC7FB40E1";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" -4.7491912841796875 -0.00035149994073435664 10.809927940368652 ;
	setAttr ".r" -type "double3" 6.8301557869108422e-06 -1.0245311031459144e-05 6.830150901574229e-06 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 0.99999970197677612 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 6.8301557869108422e-06 -1.0245311031459144e-05 6.830150901574229e-06 ;
	setAttr ".bps" -type "matrix" 2.8343698643818628e-08 0.010000013271470931 -2.5783698520402283e-08 0
		 -0.01000000216064454 2.8343768451622884e-08 3.2812769664812713e-10 0 3.2818639796319065e-10 2.7653771882902321e-08 0.010000007143027416 0
		 3.3652652121612279e-06 1.6145110919742671 0.10810087728577156 1;
	setAttr ".radi" 0.024795090928673748;
	setAttr -k on ".MaxHandle" 59;
	setAttr ".fbxID" 5;
createNode joint -n "Face_LipUpperRight" -p "Face_Hub";
	rename -uid "FBA101D9-45B7-E12A-73A5-6F8649CF6F99";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" -4.8909454345703125 1.4996494054794312 10.179598808288574 ;
	setAttr ".r" -type "double3" -2.7320740395608964e-05 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -2.7320740395608964e-05 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000002160639511 2.9535838985582261e-08 -5.6323374329943623e-09 0 -5.6322655327255545e-09 2.9441944170585519e-08 0.010000010123256324 0
		 -0.014996650672234759 1.6130935742502839 0.10179758219646343 1;
	setAttr ".radi" 0.023924780935049059;
	setAttr -k on ".MaxHandle" 60;
	setAttr ".fbxID" 5;
createNode joint -n "Face_NostrilLeft" -p "Face_Hub";
	rename -uid "3EEFF997-4D7B-25C8-CAB6-5F8DA7641C14";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" 4.2507171630859375 8.999664306640625 16.109912872314453 ;
	setAttr ".r" -type "double3" 1.4864123519152154e-13 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 1.4864123519152154e-13 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000002160641059 2.9535853024583527e-08 -8.639638659920577e-10 0 -8.6389576259256025e-10 2.9441930086805039e-08 0.010000010123257871 0
		 -0.089996551005661063 1.7045107231181706 0.16110052433856675 1;
	setAttr ".radi" 0.03976673126220704;
	setAttr -k on ".MaxHandle" 61;
	setAttr ".fbxID" 5;
createNode joint -n "Face_NostrilRight" -p "Face_Hub";
	rename -uid "90847EFA-4765-E5B2-D69A-54B0DF9C44B8";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".v" no;
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" 4.2508087158203125 -9.0003747940063477 16.109912872314453 ;
	setAttr ".r" -type "double3" 1.4864123519152154e-13 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 1.4864123519152154e-13 -3.9082660584839899e-11 -1.3027553528279965e-11 ;
	setAttr ".bps" -type "matrix" 2.9535785201214736e-08 0.010000013271462375 -2.7571844224912146e-08 0
		 -0.010000002160641059 2.9535853024583527e-08 -8.639638659920577e-10 0 -8.6389576259256025e-10 2.9441930086805039e-08 0.010000010123257871 0
		 0.09000387889513628 1.7045111070002747 0.16110053988742584 1;
	setAttr ".radi" 0.039767476022243509;
	setAttr -k on ".MaxHandle" 62;
	setAttr ".fbxID" 5;
createNode transform -n "Camera1st_free_dummy" -p "Head";
	rename -uid "E487DA11-45CB-8740-EB48-01AD0E95B000";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 5.209991455078125 -2.8300018310546875 2.3899998664855957 ;
	setAttr ".r" -type "double3" -135.62538753262112 -89.999756617644252 45.625467822027943 ;
	setAttr ".s" -type "double3" 0.99999958276748657 1.0000003576278687 1.0000001192092896 ;
	setAttr -k on ".MaxHandle" 63;
createNode locator -n "Camera1st_free_dummyShape" -p "Camera1st_free_dummy";
	rename -uid "D22A138B-4146-0927-FB39-1785727C43D8";
	setAttr -k off ".v";
createNode joint -n "LeftShoulder" -p "Spine3";
	rename -uid "EBBFB725-442E-637F-BD0F-EDB8FA401F1D";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 5;
	setAttr ".t" -type "double3" 15.486587524414062 -1.0000081062316895 5.0111885070800781 ;
	setAttr ".r" -type "double3" 2.8011638081309198 10.738588637477672 -75.286689608789089 ;
	setAttr ".s" -type "double3" 0.99999982118606567 0.9999995231628418 0.99999934434890747 ;
	setAttr ".ssc" no;
	setAttr -av ".is" -type "double3" 0.99999988079071045 1.0000001192092896 1 ;
	setAttr -av ".is";
	setAttr ".pa" -type "double3" 2.8011638081309198 10.738588637477672 -75.286689608789089 ;
	setAttr ".bps" -type "matrix" 0.0095027143337018481 0.0024953388115310717 -0.0018632700657694973 0
		 -0.0024487076882535679 0.0096836692438323265 0.00048013783748900198 0 0.001924135904607114 -1.2630203897424142e-09 0.0098131441881048765 0
		 0.0099999748693982773 1.3900002942195111 0.020000116264574784 1;
	setAttr ".radi" 0.033203896433115013;
	setAttr -k on ".MaxHandle" 64;
	setAttr ".fbxID" 5;
createNode joint -n "LeftArm" -p "LeftShoulder";
	rename -uid "D06C5282-4D7D-E8B2-7CC8-D1B5E8522B82";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 6;
	setAttr ".t" -type "double3" 15.811168670654297 0.0563201904296875 -0.057729482650756836 ;
	setAttr ".r" -type "double3" 7.3379761328845499 5.0205815541507528 -53.326245122064705 ;
	setAttr ".s" -type "double3" 1 1.0000002384185791 0.99999994039535522 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 7.3379761328845499 5.0205815541507528 -53.326245122064705 ;
	setAttr ".bps" -type "matrix" 0.0074418562456707894 -0.0062523389362992513 -0.0023509831439362319 0
		 0.0064388959976188652 0.0076511201207388087 3.4025097615933376e-05 0 0.001777487376382982 -0.0015390945920968921 0.0097196613020110265 0
		 0.16000000297497066 1.4299999032278432 -0.00999982730700456 1;
	setAttr ".radi" 0.042000041306018837;
	setAttr -k on ".MaxHandle" 65;
	setAttr ".fbxID" 5;
createNode joint -n "LeftArmRoll" -p "LeftArm";
	rename -uid "B3C568AF-408B-4774-E462-928B9249C532";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 7;
	setAttr ".t" -type "double3" 20.000007629394531 -7.62939453125e-06 3.4332275390625e-05 ;
	setAttr ".r" -type "double3" -8.9219346033232613e-05 -3.2016504101101329e-05 1.1952828197745825e-05 ;
	setAttr ".s" -type "double3" 1.0000002384185791 0.99999994039535522 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -8.9219346033232613e-05 -3.2016504101101329e-05 1.1952828197745825e-05 ;
	setAttr ".bps" -type "matrix" 0.0074418603564531107 -0.0062523396908599881 -0.0023509782660716934 0
		 0.006438891293485312 0.0076511233656546378 3.4010450861790679e-05 0 0.001777493244381481 -0.0015390791842228352 0.0097196626686952853 0
		 0.30883719656555197 1.3049529655862644 -0.057019174683809501 1;
	setAttr ".radi" 0.018900007009506229;
	setAttr -k on ".MaxHandle" 66;
	setAttr ".fbxID" 5;
createNode joint -n "LeftForeArm" -p "LeftArmRoll";
	rename -uid "3F6E135C-4559-8729-8F5D-FE947D38583B";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".t" -type "double3" 8.9999961853027344 1.52587890625e-05 1.9073486328125e-05 ;
	setAttr ".r" -type "double3" 0.00029826681325101768 -14.645630329376347 1.7648918098023059e-06 ;
	setAttr ".s" -type "double3" 1.0000001192092896 0.99999988079071045 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 0.00029826681325101768 -14.645630329376347 1.7648918098023059e-06 ;
	setAttr ".bps" -type "matrix" 0.0076494827177704117 -0.0064383306539623391 0.0001829286036396649 0
		 0.0064388894539857801 0.0076511231237866269 3.4062567611437487e-05 0 -0.0001618941143681702 9.1729834745104448e-05 0.0099982735903103651 0
		 0.37581404353786274 1.2486820196105795 -0.078177784203373055 1;
	setAttr ".radi" 0.042840017974376685;
	setAttr -k on ".MaxHandle" 67;
	setAttr ".fbxID" 5;
createNode joint -n "LeftForeArmRoll" -p "LeftForeArm";
	rename -uid "04757A8F-45DA-7652-C266-F6A217772D1B";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" 20.399993896484375 -4.57763671875e-05 2.9087066650390625e-05 ;
	setAttr ".r" -type "double3" -0.00013969871286764041 -4.1354670850033208e-06 5.1226430988428386e-06 ;
	setAttr ".s" -type "double3" 0.9999997615814209 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.00013969871286764041 -4.1354670850033208e-06 5.1226430988428386e-06 ;
	setAttr ".bps" -type "matrix" 0.0076494814579880274 -0.0064383284282601072 0.0001829292847219042 0
		 0.0064388891647813836 0.0076511234757385633 3.4038173440605792e-05 0 -0.00016187896717369845 9.1748954436435027e-05 0.0099982736601286846 0
		 0.53186314483364905 1.1173397659937299 -0.074445752544441773 1;
	setAttr ".radi" 0.014909995794296266;
	setAttr -k on ".MaxHandle" 68;
	setAttr ".fbxID" 5;
createNode joint -n "LeftHand" -p "LeftForeArmRoll";
	rename -uid "BA66EE49-4535-56CD-9EB1-C5BCE2629C5B";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" 7.0999946594238281 -1.52587890625e-05 4.76837158203125e-07 ;
	setAttr ".r" -type "double3" 1.7662440201295335e-05 4.5890344427115448e-06 -5.1226430988414872e-05 ;
	setAttr ".s" -type "double3" 0.99999964237213135 1 0.9999997615814209 ;
	setAttr ".ssc" no;
	setAttr -av ".is" -type "double3" 0.9999997615814209 1 1 ;
	setAttr -av ".is";
	setAttr ".pa" -type "double3" 1.7662440201295335e-05 4.5890344427115448e-06 -5.1226430988414872e-05 ;
	setAttr ".bps" -type "matrix" 0.0076494729784678511 -0.0064383329737169931 0.00018292838806967569 0
		 0.0064388959540476361 0.0076511177477026687 3.4041419137339211e-05 0 -0.00016188030080702481 9.1746058299244147e-05 0.0099982712805125468 0
		 0.58617432400588421 1.0716275518343366 -0.073146951351696937 1;
	setAttr ".radi" 0.0074424206838011745;
	setAttr -k on ".MaxHandle" 69;
	setAttr ".fbxID" 5;
createNode joint -n "LeftHandRing" -p "LeftHand";
	rename -uid "26EB354A-4558-AAA9-614E-7AB0B972D8D3";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 3;
	setAttr ".t" -type "double3" 3.399993896484375 1.52587890625e-05 1.0000123977661133 ;
	setAttr ".r" -type "double3" -9.5702701068244947e-05 -0.00011045696548365208 -2.5613209387546107e-05 ;
	setAttr ".s" -type "double3" 1 0.99999988079071045 1.0000003576278687 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -9.5702701068244947e-05 -0.00011045696548365208 -2.5613209387546107e-05 ;
	setAttr ".bps" -type "matrix" 0.0076494697879631252 -0.0064383362171490377 0.00018294764789622108 0
		 0.006438898876459963 0.0076511138041814846 3.4024796472327353e-05 0 -0.00016188435056890379 9.1771283052275235e-05 0.0099982745603445881 0
		 0.61202070138599107 1.0498291229627019 -0.062526600192594067 1;
	setAttr ".radi" 0.011102967895567419;
	setAttr -k on ".MaxHandle" 70;
	setAttr ".fbxID" 5;
createNode joint -n "LeftHandRing1" -p "LeftHandRing";
	rename -uid "72DC2541-468C-EA5E-7BA3-BE94CE6E2F55";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 4;
	setAttr ".t" -type "double3" 4.926483154296875 0.2920074462890625 -1.8968963623046875 ;
	setAttr ".r" -type "double3" -5.9119152721910817 1.9439825209741142 -13.25520930935209 ;
	setAttr ".s" -type "double3" 1.0000002384185791 0.99999964237213135 1.0000003576278687 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -5.9119152721910817 1.9439825209741142 -13.25520930935209 ;
	setAttr ".bps" -type "matrix" 0.0059713652348250571 -0.0080196227423991687 -0.00016899124415271886 0
		 0.0079744378000713156 0.0059578562171978388 -0.00095515117509720692 0 0.00086667432286277081 0.00043559549720068882 0.0099528548727778714 0
		 0.65189296968923105 1.0201708696374578 -0.080581066836027865 1;
	setAttr ".radi" 0.0099143817275762578;
	setAttr -k on ".MaxHandle" 71;
	setAttr ".fbxID" 5;
createNode joint -n "LeftHandRing2" -p "LeftHandRing1";
	rename -uid "B2ACDC88-44A7-58FD-AC88-37BBF3BFAE9B";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 5;
	setAttr ".t" -type "double3" 4.72113037109375 0.0006561279296875 -6.5326690673828125e-05 ;
	setAttr ".r" -type "double3" -0.93972414113326297 -0.34194651306507284 -19.997184589399023 ;
	setAttr ".s" -type "double3" 0.99999994039535522 0.9999997615814209 0.99999958276748657 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.93972414113326297 -0.34194651306507284 -19.997184589399023 ;
	setAttr ".bps" -type "matrix" 0.0028894188817355664 -0.0095707760906386177 0.0002272303760655582 0
		 0.0095204896636176331 0.0028476856786037166 -0.0011184393184839514 0 0.0010057213371110112 0.0005394991583688787 0.0099346650074964918 0
		 0.68008973909065573 0.98231306580345579 -0.081380173419680832 1;
	setAttr ".radi" 0.0057572465948760518;
	setAttr -k on ".MaxHandle" 72;
	setAttr ".fbxID" 5;
createNode joint -n "LeftHandRing3" -p "LeftHandRing2";
	rename -uid "91155140-44B5-ED85-9983-3DB3DAB9D475";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 6;
	setAttr ".t" -type "double3" 2.7398681640625 -0.0957794189453125 -0.00035333633422851562 ;
	setAttr ".r" -type "double3" -0.98477555722297838 -0.17362198528492609 -9.9985008767038792 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1.0000001192092896 0.99999982118606567 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.98477555722297838 -0.17362198528492609 -9.9985008767038792 ;
	setAttr ".bps" -type "matrix" 0.0011956069403113018 -0.0099181590648114749 0.00044806817702020528 0
		 0.009858882516907478 0.0011327771935687628 -0.0012325656440202427 0 0.0011717177098153197 0.00058911212276461307 0.0099136315745847418 0
		 0.6870941435714174 0.95581746078305396 -0.080653978956456415 1;
	setAttr ".radi" 0.0052243027277290828;
	setAttr -k on ".MaxHandle" 73;
	setAttr ".fbxID" 5;
createNode transform -n "LeftHandRing4" -p "LeftHandRing3";
	rename -uid "13D3F77F-41CF-CABE-1818-91A7B35F3C7F";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" 2.48590087890625 -0.096160888671875 -0.00035381317138671875 ;
	setAttr ".r" -type "double3" -3.6552171158076964e-06 3.180306832286859e-05 -1.7075472925031871e-06 ;
	setAttr ".s" -type "double3" 1.0000001192092896 1.0000003576278687 1.0000003576278687 ;
	setAttr -k on ".MaxHandle" 74;
createNode locator -n "LeftHandRing4Shape" -p "LeftHandRing4";
	rename -uid "6B5FC86B-47CF-CB8D-A506-F18792E5F9EB";
	setAttr -k off ".v";
createNode joint -n "LeftHandMiddle1" -p "LeftHand";
	rename -uid "16828CD2-4B83-A2AC-BFF9-10BE5A2E8166";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 3;
	setAttr ".t" -type "double3" 8.6901321411132812 0.4558258056640625 1.4039082527160645 ;
	setAttr ".r" -type "double3" -1.9731321412745804 -3.3453987290770804 -12.890775627341432 ;
	setAttr ".s" -type "double3" 0.99999964237213135 0.99999994039535522 1.0000001192092896 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -1.9731321412745804 -3.3453987290770804 -12.890775627341432 ;
	setAttr ".bps" -type "matrix" 0.0060005027108359418 -0.0079640201043106717 0.00075388209971824082 0
		 0.0079960887503523429 0.005999175496487312 -0.00026936958305343278 0 -0.00023774301018745451 0.00076444701109267292 0.0099679072674991633 0
		 0.65535700484423087 1.0192939674842267 -0.057505106966100804 1;
	setAttr ".radi" 0.010680972933769229;
	setAttr -k on ".MaxHandle" 75;
	setAttr ".fbxID" 5;
createNode joint -n "LeftHandMiddle2" -p "LeftHandMiddle1";
	rename -uid "687A4617-45DF-00D6-0D73-64BB4281F501";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 4;
	setAttr ".t" -type "double3" 5.0861778259277344 0.003143310546875 0.0016827583312988281 ;
	setAttr ".r" -type "double3" -0.00016733966540183147 -3.9273589741280077e-05 -20.000012622873601 ;
	setAttr ".s" -type "double3" 1 0.9999997615814209 0.99999970197677612 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.00016733966540183147 -3.9273589741280077e-05 -20.000012622873601 ;
	setAttr ".bps" -type "matrix" 0.0029038024274484768 -0.0095355699048413674 0.00080055410094806488 0
		 0.0095661574443542414 0.0029135206192011727 4.6893170391295594e-06 0 -0.00023771699056951797 0.0007644618287702637 0.0099679037618295024 0
		 0.68590136280257552 0.97880768867562651 -0.053654801680401466 1;
	setAttr ".radi" 0.006293933037668468;
	setAttr -k on ".MaxHandle" 76;
	setAttr ".fbxID" 5;
createNode joint -n "LeftHandMiddle3" -p "LeftHandMiddle2";
	rename -uid "1C1C3126-46DA-969D-0B59-8CAF9D70A01E";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 5;
	setAttr ".t" -type "double3" 2.997100830078125 -0.00431060791015625 -0.00014400482177734375 ;
	setAttr ".r" -type "double3" 1.3820466892260734e-05 -2.9882094008646329e-06 -10.000006461136568 ;
	setAttr ".s" -type "double3" 0.99999964237213135 0.99999964237213135 1.0000002384185791 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 1.3820466892260734e-05 -2.9882094008646329e-06 -10.000006461136568 ;
	setAttr ".bps" -type "matrix" 0.0011985397760196715 -0.009896627275451552 0.00078757781597091694 0
		 0.0099250625459030347 0.001213421991778879 0.00014363527836000413 0 -0.00023771950380654358 0.00076446223448920446 0.00996790606264116 0
		 0.69456314974670763 0.95021595506734147 -0.051256915959939413 1;
	setAttr ".radi" 0.0052718500234186652;
	setAttr -k on ".MaxHandle" 77;
	setAttr ".fbxID" 5;
createNode transform -n "LeftHandMiddle4" -p "LeftHandMiddle3";
	rename -uid "941D3A67-4AC9-9655-D380-549C640D8D42";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" 2.509185791015625 0.07819366455078125 -0.0001468658447265625 ;
	setAttr ".r" -type "double3" 4.8558399285008423e-06 1.280660545710707e-06 -1.7075473942809432e-06 ;
	setAttr ".s" -type "double3" 1 0.99999970197677612 1 ;
	setAttr -k on ".MaxHandle" 78;
createNode locator -n "LeftHandMiddle4Shape" -p "LeftHandMiddle4";
	rename -uid "9325D092-46F4-43D3-2644-76B7F4CE354B";
	setAttr -k off ".v";
createNode joint -n "LeftHandIndex1" -p "LeftHand";
	rename -uid "92DAF2F8-4C77-E832-25B4-D092568E5B07";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 3;
	setAttr ".t" -type "double3" 8.6193962097167969 0.15291595458984375 3.7471106052398682 ;
	setAttr ".r" -type "double3" 1.9977297869826507 -9.6468171205714874 -13.340858305735351 ;
	setAttr ".s" -type "double3" 0.99999988079071045 1.0000004768371582 1.0000002384185791 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 1.9977297869826507 -9.6468171205714874 -13.340858305735351 ;
	setAttr ".bps" -type "matrix" 0.0058459467968508408 -0.0079011142786440582 0.0018431850127013951 0
		 0.0079849664181294612 0.0060054870553860667 0.00041790308421586205 0 -0.0014371131408654877 0.0012274731043442847 0.0098197821549317957 0
		 0.65248618893220556 1.0176467696058968 -0.034100385271542827 1;
	setAttr ".radi" 0.0093663470819592472;
	setAttr -k on ".MaxHandle" 79;
	setAttr ".fbxID" 5;
createNode joint -n "LeftHandIndex2" -p "LeftHandIndex1";
	rename -uid "A829F512-4E2E-A147-968B-619E2C33F241";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 4;
	setAttr ".t" -type "double3" 4.4601631164550781 0.00113677978515625 -3.528594970703125e-05 ;
	setAttr ".r" -type "double3" -0.00027939748136831697 -1.7075477455613401e-05 -19.999978926905964 ;
	setAttr ".s" -type "double3" 0.99999970197677612 0.99999982118606567 0.99999958276748657 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.00027939748136831697 -1.7075477455613401e-05 -19.999978926905964 ;
	setAttr ".bps" -type "matrix" 0.0027623759512804148 -0.0094786120547132799 0.0015890989116476 0
		 0.0095028498742810198 0.0029409686067513761 0.0010230581940084212 0 -0.0014370670247817905 0.0012274897584176375 0.0098197825731740438 0
		 0.67856919307458963 0.9824132947251224 -0.025879350897650241 1;
	setAttr ".radi" 0.0055638753622770324;
	setAttr -k on ".MaxHandle" 80;
	setAttr ".fbxID" 5;
createNode joint -n "LeftHandIndex3" -p "LeftHandIndex2";
	rename -uid "426B5EC4-4AAF-D09D-8894-7F9C60D8031F";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 5;
	setAttr ".t" -type "double3" 2.6494598388671875 0.00736236572265625 -0.00024890899658203125 ;
	setAttr ".r" -type "double3" 8.2175664535608265e-06 -1.2806605571545099e-06 -10.000005080145387 ;
	setAttr ".s" -type "double3" 0.99999988079071045 1.0000004768371582 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 8.2175664535608265e-06 -1.2806605571545099e-06 -10.000005080145387 ;
	setAttr ".bps" -type "matrix" 0.0010702556582355134 -0.0098453033881884706 0.0013873046777683655 0
		 0.00983816636186002 0.001250344874506608 0.0012834619147785073 0 -0.0014370684597283651 0.0012274897991485043 0.0098197823580868353 0
		 0.68595831837245269 0.95732143971117489 -0.021664009254899461 1;
	setAttr ".radi" 0.0045862549915909765;
	setAttr -k on ".MaxHandle" 81;
	setAttr ".fbxID" 5;
createNode transform -n "LeftHandIndex4" -p "LeftHandIndex3";
	rename -uid "A9B00F9A-4DAA-9039-F3EF-5E88EE635DDA";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" 2.1821212768554688 0.0890350341796875 -0.000247955322265625 ;
	setAttr ".r" -type "double3" 5.6562504064168006e-06 2.5613212440880655e-06 4.2688687401467799e-07 ;
	setAttr ".s" -type "double3" 0.99999988079071045 1 1.0000002384185791 ;
	setAttr -k on ".MaxHandle" 82;
createNode locator -n "LeftHandIndex4Shape" -p "LeftHandIndex4";
	rename -uid "FABAC24A-4B47-59AC-35AA-B7945869AA41";
	setAttr -k off ".v";
createNode joint -n "LeftHandThumb1" -p "LeftHand";
	rename -uid "EA5CDC9F-464F-AB16-94FE-BAA8C96E5D61";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 3;
	setAttr ".t" -type "double3" 1.5000762939453125 -1.7675247192382812 3.0000720024108887 ;
	setAttr ".r" -type "double3" 88.174094765053781 -31.806099965624405 -21.391677013521914 ;
	setAttr ".s" -type "double3" 1.0000002384185791 0.9999997615814209 0.99999982118606567 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 88.174094765053781 -31.806099965624405 -21.391677013521914 ;
	setAttr ".bps" -type "matrix" 0.0039717674726682944 -0.0074178602969908391 0.0054037505545868406 0
		 -0.002372395077332683 0.0048580924664528447 0.008412532761231396 0 -0.0088654838930058624 -0.0046232504961789536 0.00016971406713572933 0
		 0.58578255676048352 1.0487212661999052 -0.042937180121892626 1;
	setAttr ".radi" 0.010976849980652334;
	setAttr -k on ".MaxHandle" 83;
	setAttr ".fbxID" 5;
createNode joint -n "LeftHandThumb2" -p "LeftHandThumb1";
	rename -uid "CEA02DBD-4B10-A19A-EE73-B1B10470EAC8";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 4;
	setAttr ".t" -type "double3" 5.2257804870605469 0.11587142944335938 0.0018768310546875 ;
	setAttr ".r" -type "double3" -0.16996427898284872 0.47339869708252102 -16.726406127340216 ;
	setAttr ".s" -type "double3" 1.0000005960464478 0.99999982118606567 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.16996427898284872 0.47339869708252102 -16.726406127340216 ;
	setAttr ".bps" -type "matrix" 0.004559600304188189 -0.0084636949505947461 0.0027524799267607514 0
		 -0.0011027434552480203 0.0025315828343970793 0.0096111930056618257 0 -0.0088314226602311148 -0.0046858508498477209 0.00022097428772672347 0
		 0.60624660989399515 1.0105113936625005 -0.013723275195875517 1;
	setAttr ".radi" 0.0073076574504375479;
	setAttr -k on ".MaxHandle" 84;
	setAttr ".fbxID" 5;
createNode joint -n "LeftHandThumb3" -p "LeftHandThumb2";
	rename -uid "29267A96-494C-5113-42BF-109B88F4448F";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 5;
	setAttr ".t" -type "double3" 3.4798355102539062 -0.000797271728515625 0.00022125244140625 ;
	setAttr ".r" -type "double3" 0.00096006777842608509 8.5377384980713482e-06 2.561321549421424e-06 ;
	setAttr ".s" -type "double3" 0.9999997615814209 1.0000007152557373 1.0000001192092896 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 0.00096006777842608509 8.5377384980713482e-06 2.561321549421424e-06 ;
	setAttr ".bps" -type "matrix" 0.00455960048378276 -0.0084636921212757586 0.0027524796672444389 0
		 -0.0011028924301155804 0.0025315065053228181 0.0096112034584585563 0 -0.0088314045543911399 -0.0046858950890597117 0.00022081367571834021 0
		 0.62211219415742969 0.98105607231010139 -0.0041527116468324573 1;
	setAttr ".radi" 0.0063623081892728818;
	setAttr -k on ".MaxHandle" 85;
	setAttr ".fbxID" 5;
createNode transform -n "LeftHandThumb4" -p "LeftHandThumb3";
	rename -uid "E93E68E1-471C-E378-E60C-809CCF8A96E9";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" 3.02886962890625 -0.069158554077148438 0.0037384033203125 ;
	setAttr ".r" -type "double3" 0.00035687746921478624 -3.4150909210113076e-06 1.7075454605056561e-06 ;
	setAttr ".s" -type "double3" 1.0000009536743164 0.99999970197677612 0.99999970197677612 ;
	setAttr -k on ".MaxHandle" 86;
createNode locator -n "LeftHandThumb4Shape" -p "LeftHandThumb4";
	rename -uid "AA6B6A2E-43A7-06BB-D6D3-9CBE262E34FD";
	setAttr -k off ".v";
createNode transform -n "LeftHandPinky" -p "LeftHand";
	rename -uid "2FA13526-41FF-4AA3-6EEF-61A0BFFD8196";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" 3.399993896484375 1.52587890625e-05 1.0000123977661133 ;
	setAttr ".r" -type "double3" -9.5702701068244947e-05 -0.00011045696548365208 -2.5613209387546107e-05 ;
	setAttr ".s" -type "double3" 1 0.99999988079071045 1.0000003576278687 ;
	setAttr -k on ".MaxHandle" 87;
createNode locator -n "LeftHandPinkyShape" -p "LeftHandPinky";
	rename -uid "12CEBA38-4D93-BC53-85C5-35A2B0CC07DD";
	setAttr -k off ".v";
createNode joint -n "LeftHandPinky1" -p "LeftHandPinky";
	rename -uid "432A4ED8-4664-2104-A736-25A4C1F4E9F1";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 4;
	setAttr ".t" -type "double3" 4.1253852844238281 -0.257965087890625 -3.9290180206298828 ;
	setAttr ".r" -type "double3" -10.442077074830374 8.0233408789496306 -14.640242555690218 ;
	setAttr ".s" -type "double3" 1.0000004768371582 1.0000001192092896 1.0000007152557373 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -10.442077074830374 8.0233408789496306 -14.640242555690218 ;
	setAttr ".bps" -type "matrix" 0.0057397619144976065 -0.0080960135056931809 -0.0012287653015773357 0
		 0.0079110381944598619 0.0058697981409484862 -0.0017207748138711348 0 0.0021143968187599962 1.5603910845452481e-05 0.0097739107008307149 0
		 0.64255274689895714 1.0209342142064568 -0.10106404879055469 1;
	setAttr ".radi" 0.0078054364398121856;
	setAttr -k on ".MaxHandle" 88;
	setAttr ".fbxID" 5;
createNode joint -n "LeftHandPinky2" -p "LeftHandPinky1";
	rename -uid "679F4D5A-47E5-C1E9-61A5-61BACB86A2C8";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 5;
	setAttr ".t" -type "double3" 3.7168731689453125 -0.0001678466796875 -2.6226043701171875e-05 ;
	setAttr ".r" -type "double3" -2.8193930627499486 -1.0255937828306052 -19.979781838078612 ;
	setAttr ".s" -type "double3" 0.99999970197677612 0.99999964237213135 1.0000002384185791 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -2.8193930627499486 -1.0255937828306052 -19.979781838078612 ;
	setAttr ".bps" -type "matrix" 0.0027286070179006181 -0.0096125610879372811 -0.00039180642902439638 0
		 0.0092831158851561166 0.0027376371182359612 -0.0025157748640858304 0 0.0025255625564988083 0.0003227388030153493 0.0096704531974397684 0
		 0.66388533066133026 0.99084137319636967 -0.10563118107558866 1;
	setAttr ".radi" 0.0043436071649193761;
	setAttr -k on ".MaxHandle" 89;
	setAttr ".fbxID" 5;
createNode joint -n "LeftHandPinky3" -p "LeftHandPinky2";
	rename -uid "5E83A2FD-4BDB-B8C6-571B-B7844FDF919A";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 6;
	setAttr ".t" -type "double3" 2.0683822631835938 0.00022125244140625 3.528594970703125e-05 ;
	setAttr ".r" -type "double3" -2.9544467998825259 -0.52092483125822142 -9.9815569756296707 ;
	setAttr ".s" -type "double3" 0.99999994039535522 0.99999946355819702 1.0000004768371582 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -2.9544467998825259 -0.52092483125822142 -9.9815569756296707 ;
	setAttr ".bps" -type "matrix" 0.0011011695088776747 -0.0099382335980275158 0.00013810535444365636 0
		 0.0094731079210622123 0.0010073804749770598 -0.0030406123201715696 0 0.0030079174280981062 0.00046565316384507185 0.0095255435923118775 0
		 0.66953127604928098 0.97095953943535263 -0.10644180193418956 1;
	setAttr ".radi" 0.0043435887806117547;
	setAttr -k on ".MaxHandle" 90;
	setAttr ".fbxID" 5;
createNode transform -n "LeftHandPinky4" -p "LeftHandPinky3";
	rename -uid "C20F0B4E-4430-698C-28A4-80B52A4E25C6";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" 2.0670928955078125 0.07257843017578125 2.09808349609375e-05 ;
	setAttr ".r" -type "double3" -1.4941035247184111e-06 2.6680431216193255e-05 4.2688689945912294e-07 ;
	setAttr ".s" -type "double3" 0.99999982118606567 1.0000002384185791 1.0000001192092896 ;
	setAttr -k on ".MaxHandle" 91;
createNode locator -n "LeftHandPinky4Shape" -p "LeftHandPinky4";
	rename -uid "3C956BC5-4716-18AF-8B5B-DEA7FF9D81AD";
	setAttr -k off ".v";
createNode transform -n "LeftHand_Dummy" -p "LeftHand";
	rename -uid "81ECA700-4D02-E201-9AF7-87885934AB15";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 10.835899353027344 0.22370147705078125 0.61082220077514648 ;
	setAttr ".r" -type "double3" 179.99992300029436 -7.7639986949845939e-06 15.000125353215886 ;
	setAttr ".s" -type "double3" 1.0000005960464478 1.0000001192092896 0.99999898672103882 ;
	setAttr -k on ".MaxHandle" 92;
createNode locator -n "LeftHand_DummyShape" -p "LeftHand_Dummy";
	rename -uid "E4841FBC-49EE-ABCF-2F5F-A8BF61C923DD";
	setAttr -k off ".v";
createNode joint -n "LeftWristExtra" -p "LeftForeArmRoll";
	rename -uid "686AF404-437D-97F4-A707-A092EB42BD47";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" 6.1000022888183594 1.52587890625e-05 -2.384185791015625e-06 ;
	setAttr ".r" -type "double3" 8.6444571377966267e-06 2.5613197174220361e-06 -2.9028290130784337e-05 ;
	setAttr ".s" -type "double3" 1.0000003576278687 1 0.99999958276748657 ;
	setAttr ".ssc" no;
	setAttr -av ".is" -type "double3" 0.9999997615814209 1 1 ;
	setAttr -av ".is";
	setAttr ".pa" -type "double3" 8.6444571377966267e-06 2.5613197174220361e-06 -2.9028290130784337e-05 ;
	setAttr ".bps" -type "matrix" 0.0076494809386962667 -0.0064383346112472069 0.00018292888593980116 0
		 0.0064388930158846332 0.0076511202276701891 3.4039774601686677e-05 0 -0.0001618795291371937 9.1747473983702968e-05 0.0099982694915657852 0
		 0.57852509787125073 1.0780660643733115 -0.073329906807306944 1;
	setAttr ".radi" 0.012810019701719286;
	setAttr -k on ".MaxHandle" 93;
	setAttr ".fbxID" 5;
createNode joint -n "LeftForeArmExtra" -p "LeftForeArm";
	rename -uid "8090188F-4DD2-0D6C-DCA0-31B889C9989D";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" 12.399997711181641 7.62939453125e-06 -3.337860107421875e-06 ;
	setAttr ".r" -type "double3" -6.9822709301540432e-05 -1.0672166761480665e-07 -1.7075466818369067e-06 ;
	setAttr ".s" -type "double3" 1.0000003576278687 0.9999995231628418 0.99999982118606567 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -6.9822709301540432e-05 -1.0672166761480665e-07 -1.7075466818369067e-06 ;
	setAttr ".bps" -type "matrix" 0.0076494852615447495 -0.0064383331845100436 0.00018292866804488783 0
		 0.0064388868089413362 0.0076511191717788486 3.4050372568782365e-05 0 -0.00016188623875666865 9.1739142275942178e-05 0.0099982718439821788 0
		 0.47066766139514726 1.1688467923048713 -0.075909503049893357 1;
	setAttr ".radi" 0.026040001139044765;
	setAttr -k on ".MaxHandle" 94;
	setAttr ".fbxID" 5;
createNode joint -n "LeftElbowExtra" -p "LeftArmRoll";
	rename -uid "4A69FC86-4382-D159-3496-088637ACD234";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".t" -type "double3" 9.4999961853027344 2.288818359375e-05 7.62939453125e-06 ;
	setAttr ".r" -type "double3" 0.00019453959432563892 -7.322800802875757 -8.607943892546242e-06 ;
	setAttr ".s" -type "double3" 1.0000001192092896 0.99999982118606567 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 0.00019453959432563892 -7.322800802875757 -8.607943892546242e-06 ;
	setAttr ".bps" -type "matrix" 0.0076077210773887868 -0.0063975162425092408 -0.0010929417357442614 0
		 0.0064388940255128658 0.0076511185808751632 3.4043841553351371e-05 0 0.0008144394372725821 -0.00072963299852470825 0.0099400411254199697 0
		 0.37953500249913547 1.2455559257519515 -0.079353384309641575 1;
	setAttr ".radi" 0.019950001314282418;
	setAttr -k on ".MaxHandle" 95;
	setAttr ".fbxID" 5;
createNode joint -n "LeftArmExtra" -p "LeftArm";
	rename -uid "2A52A25C-4AF2-091D-DCAA-08B41C8D2D17";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 7;
	setAttr ".t" -type "double3" 13 3.0517578125e-05 1.9073486328125e-06 ;
	setAttr ".r" -type "double3" -4.5249992462886091e-05 8.5377354447385272e-07 5.1226412668431233e-06 ;
	setAttr ".s" -type "double3" 1.0000001192092896 1.0000001192092896 0.99999964237213135 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -4.5249992462886091e-05 8.5377354447385272e-07 5.1226412668431233e-06 ;
	setAttr ".bps" -type "matrix" 0.0074418577084913191 -0.006252338997572663 -0.0023509834211531719 0
		 0.0064388946960482448 0.0076511228073412223 3.4017635652508199e-05 0 0.0017774918258922892 -0.0015390879991160193 0.0097196578528581032 0
		 0.25674433405849068 1.348719727614019 -0.040562588601029306 1;
	setAttr ".radi" 0.027300014644861224;
	setAttr -k on ".MaxHandle" 96;
	setAttr ".fbxID" 5;
createNode joint -n "RightShoulder" -p "Spine3";
	rename -uid "24457F4D-4CF7-B47D-9558-AB9E131F39D4";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 5;
	setAttr ".t" -type "double3" 15.486663818359375 0.99999094009399414 5.0112037658691406 ;
	setAttr ".r" -type "double3" -177.01700211034381 -11.171464330568913 -105.0545224741452 ;
	setAttr ".s" -type "double3" 0.9999995231628418 0.99999898672103882 0.9999997615814209 ;
	setAttr ".ssc" no;
	setAttr -av ".is" -type "double3" 0.99999988079071045 1.0000001192092896 1 ;
	setAttr -av ".is";
	setAttr ".pa" -type "double3" -177.01700211034381 -11.171464330568913 -105.0545224741452 ;
	setAttr ".bps" -type "matrix" 0.0094738053615824602 -0.0025481788721359402 0.0019374747745182477 0
		 -0.0024965070904804437 -0.0096698938055230724 -0.00051053906392885316 0 0.0020036105099117685 -1.6814208644490655e-08 -0.0097972305147529942 0
		 -0.010000024682867835 1.3900010817558983 0.020000236057029143 1;
	setAttr ".radi" 0.033203927725553514;
	setAttr -k on ".MaxHandle" 97;
	setAttr ".fbxID" 5;
createNode joint -n "RightArm" -p "RightShoulder";
	rename -uid "45CF1C3F-454D-F9E6-3F8C-34ADEE2EEAB2";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 6;
	setAttr ".t" -type "double3" -15.811222076416016 0.029998779296875 -0.06622314453125 ;
	setAttr ".r" -type "double3" 7.630466539636374 4.6591105365985133 -53.614613036982234 ;
	setAttr ".s" -type "double3" 1 0.9999997615814209 1.0000002384185791 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 7.630466539636374 4.6591105365985133 -53.614613036982234 ;
	setAttr ".bps" -type "matrix" 0.0074418313221659409 0.0062523591361717907 0.0023509892638248165 0
		 0.006438915312060165 -0.0076510929087687061 -3.4015792357694518e-05 0 0.0017774950551282353 0.0015390963336801853 -0.0097196667561858692 0
		 -0.16000004271719148 1.4300008198970646 -0.010000120006649692 1;
	setAttr ".radi" 0.027300033420324325;
	setAttr -k on ".MaxHandle" 98;
	setAttr ".fbxID" 5;
createNode joint -n "RightArmExtra" -p "RightArm";
	rename -uid "ECE05D68-48B2-64AD-FB15-7F8D2A2DE02F";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 7;
	setAttr ".t" -type "double3" -13.000007629394531 -2.288818359375e-05 0 ;
	setAttr ".r" -type "double3" -3.4150958063397834e-06 8.5377313736313853e-07 8.537731373631418e-06 ;
	setAttr ".s" -type "double3" 1.0000005960464478 0.99999970197677612 1.0000001192092896 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -3.4150958063397834e-06 8.5377313736313853e-07 8.537731373631418e-06 ;
	setAttr ".bps" -type "matrix" 0.0074418367173161321 0.006252361722766487 0.0023509906600548418 0
		 0.0064389121782485251 -0.0076510916519758089 -3.4015553207265748e-05 0 0.0017774956508115316 0.001539096061113815 -0.0097196679168879418 0
		 -0.25674405405709172 1.3487202785447359 -0.040562997594437239 1;
	setAttr ".radi" 0.027300033420324325;
	setAttr -k on ".MaxHandle" 99;
	setAttr ".fbxID" 5;
createNode joint -n "RightArmRoll" -p "RightArm";
	rename -uid "702C00EC-41BC-FF40-F2FE-FA8C263EDBD4";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 7;
	setAttr ".t" -type "double3" -20.000022888183594 0 1.33514404296875e-05 ;
	setAttr ".r" -type "double3" -6.403303873549716e-06 -2.9882074056559949e-05 -7.0009430646821358e-05 ;
	setAttr ".s" -type "double3" 1.0000001192092896 0.99999988079071045 1.0000001192092896 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -6.403303873549716e-06 -2.9882074056559949e-05 -7.0009430646821358e-05 ;
	setAttr ".bps" -type "matrix" 0.0074418252686508811 0.0062523700330406901 0.0023509845164449974 0
		 0.0064389234389625929 -0.0076510845289627649 -3.4011829383141921e-05 0 0.0017774921054146604 0.0015390924012145567 -0.0097196691447967668 0
		 -0.3088368157583925 1.3049535146176381 -0.057020088864571619 1;
	setAttr ".radi" 0.018900064900517467;
	setAttr -k on ".MaxHandle" 100;
	setAttr ".fbxID" 5;
createNode joint -n "RightForeArm" -p "RightArmRoll";
	rename -uid "7B1DC333-4D45-7AB9-2BAD-E7A7B25E9CE3";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".t" -type "double3" -9.0000381469726562 -5.340576171875e-05 -7.62939453125e-06 ;
	setAttr ".r" -type "double3" 0.00022149401830180026 -14.645757688144219 -6.1771228565055515e-05 ;
	setAttr ".s" -type "double3" 1.0000003576278687 1.0000001192092896 1.0000003576278687 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 0.00022149401830180026 -14.645757688144219 -6.1771228565055515e-05 ;
	setAttr ".bps" -type "matrix" 0.0076494430378185345 0.0064383728918085423 -0.00018294642537876327 0
		 0.0064389316038577938 -0.0076510790550368179 -3.4047950173130654e-05 0 -0.00016189297314053437 -9.175146053288564e-05 -0.0099982846605385992 0
		 -0.37581388449615494 1.2486823426809373 -0.078178963223900388 1;
	setAttr ".radi" 0.042839964777231218;
	setAttr -k on ".MaxHandle" 101;
	setAttr ".fbxID" 5;
createNode joint -n "RightForeArmRoll" -p "RightForeArm";
	rename -uid "46A42465-4B4A-E8E1-25BE-B282BD862194";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" -20.399971008300781 7.62939453125e-06 0 ;
	setAttr ".r" -type "double3" -0.0002129098157234506 2.7187354547822151e-05 0 ;
	setAttr ".s" -type "double3" 1 0.99999988079071045 0.9999997615814209 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.0002129098157234506 2.7187354547822151e-05 0 ;
	setAttr ".bps" -type "matrix" 0.0076494431146373219 0.006438372935344697 -0.00018294168110416875 0
		 0.0064389314378099282 -0.0076510778019693443 -3.4010792719390769e-05 0 -0.00016186537789560459 -9.1776814822055216e-05 -0.0099982824900226776 0
		 -0.53186225157215172 1.1173396639743127 -0.074446861709866599 1;
	setAttr ".radi" 0.014910144433379175;
	setAttr -k on ".MaxHandle" 102;
	setAttr ".fbxID" 5;
createNode joint -n "RightHand" -p "RightForeArmRoll";
	rename -uid "B25496FA-41A3-D26F-D477-D9843F341241";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" -7.1000595092773438 0 -6.67572021484375e-06 ;
	setAttr ".r" -type "double3" -2.4012378075831372e-07 2.5586522860798283e-05 3.415093770784567e-06 ;
	setAttr ".s" -type "double3" 1.0000002384185791 1.0000002384185791 1.0000003576278687 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -2.4012378075831372e-07 2.5586522860798283e-05 3.415093770784567e-06 ;
	setAttr ".bps" -type "matrix" 0.0076494453944802136 0.0064383740553166924 -0.00018293726182328881 0
		 0.0064389325170284614 -0.0076510800098853601 -3.4010789924021662e-05 0 -0.00016186201977708264 -9.1773972464966603e-05 -0.009998286147382263 0
		 -0.58617375181834053 1.0716268336031212 -0.073147898141563236 1;
	setAttr ".radi" 0.0074424957856535938;
	setAttr -k on ".MaxHandle" 103;
	setAttr ".fbxID" 5;
createNode joint -n "RightHandRing" -p "RightHand";
	rename -uid "28CEA4C2-4AF8-700C-0EEA-9E81F1F46DF4";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 3;
	setAttr ".t" -type "double3" -3.4000473022460938 -7.62939453125e-06 -0.99995613098144531 ;
	setAttr ".r" -type "double3" -9.1914074582773579e-05 -8.028137446317008e-05 -3.5858480318570373e-05 ;
	setAttr ".s" -type "double3" 1.0000003576278687 0.99999994039535522 1.0000002384185791 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -9.1914074582773579e-05 -8.028137446317008e-05 -3.5858480318570373e-05 ;
	setAttr ".bps" -type "matrix" 0.0076494438735310762 0.0064383810176787378 -0.00018295131530765335 0
		 0.0064389371802993783 -0.0076510753771487413 -3.3994863106213955e-05 0 -0.00016186244720444137 -9.1795289522308876e-05 -0.009998288329370152 0
		 -0.61202042220162922 1.0498278855850292 -0.062528055006157185 1;
	setAttr ".radi" 0.011102554835379124;
	setAttr -k on ".MaxHandle" 104;
	setAttr ".fbxID" 5;
createNode joint -n "RightHandRing1" -p "RightHandRing";
	rename -uid "EE28A14A-49AA-75C9-7344-CDAC685161D7";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 4;
	setAttr ".t" -type "double3" -4.9263114929199219 -0.29218292236328125 1.8967471122741699 ;
	setAttr ".r" -type "double3" -5.9116922709030852 1.9440638394989658 -13.255198259707415 ;
	setAttr ".s" -type "double3" 1 0.9999997615814209 0.99999958276748657 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -5.9116922709030852 1.9440638394989658 -13.255198259707415 ;
	setAttr ".bps" -type "matrix" 0.0059713305692641015 0.0080196550139446827 0.00016899541974970981 0
		 0.0079744691394198746 -0.0059578115581810842 0.00095514215771121602 0 0.00086667483237255912 -0.00043557862826538882 -0.0099528617624105847 0
		 -0.65189232508182537 1.0201718162944362 -0.08058107163688194 1;
	setAttr ".radi" 0.0099147838354110736;
	setAttr -k on ".MaxHandle" 105;
	setAttr ".fbxID" 5;
createNode joint -n "RightHandRing2" -p "RightHandRing1";
	rename -uid "B8AFA112-498E-3E27-25FB-B7A8DBEDD40F";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 5;
	setAttr ".t" -type "double3" -4.7213134765625 -0.0005035400390625 -3.9577484130859375e-05 ;
	setAttr ".r" -type "double3" -0.93980578312148599 -0.34197381245510267 -19.99717423047603 ;
	setAttr ".s" -type "double3" 0.99999994039535522 0.99999982118606567 0.99999916553497314 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.93980578312148599 -0.34197381245510267 -19.99717423047603 ;
	setAttr ".bps" -type "matrix" 0.0028893777214867712 0.0095707904935748069 -0.00022722797864880613 0
		 0.0095205058795499679 -0.002847634015305574 0.0011184466387073179 0 0.0010057341444586528 -0.00053948992996083879 -0.0099346662069727826 0
		 -0.68008889833681296 0.98231152823548817 -0.081379039032714526 1;
	setAttr ".radi" 0.005756985303014518;
	setAttr -k on ".MaxHandle" 106;
	setAttr ".fbxID" 5;
createNode joint -n "RightHandRing3" -p "RightHandRing2";
	rename -uid "F42EAE7C-4406-9472-0B61-AA893E73DC37";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 6;
	setAttr ".t" -type "double3" -2.7397537231445312 0.0955352783203125 0.0006961822509765625 ;
	setAttr ".r" -type "double3" -0.98480335504085703 -0.17365082071191862 -9.998521153361672 ;
	setAttr ".s" -type "double3" 0.99999982118606567 1.0000003576278687 0.9999997615814209 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.98480335504085703 -0.17365082071191862 -9.998521153361672 ;
	setAttr ".bps" -type "matrix" 0.0011955604949685243 0.0099181632424436596 -0.00044807241222188785 0
		 0.0098588933307235203 -0.0011327203688354394 0.0012325782406720071 0 0.0011717349277697506 -0.00058910744028476574 -0.0099136312331631893 0
		 -0.68709483735361365 0.9558174942557599 -0.080656555559576196 1;
	setAttr ".radi" 0.0049189327284693716;
	setAttr -k on ".MaxHandle" 107;
	setAttr ".fbxID" 5;
createNode transform -n "RightHandRing4" -p "RightHandRing3";
	rename -uid "81FA5414-4F79-BF04-AB9E-329D219B015D";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" -2.3403472900390625 0.0957489013671875 0.014228343963623047 ;
	setAttr ".r" -type "double3" -3.0949283608294102e-06 -5.9764155237611351e-06 0 ;
	setAttr ".s" -type "double3" 1 1.0000002384185791 0.99999982118606567 ;
	setAttr -k on ".MaxHandle" 108;
createNode locator -n "RightHandRing4Shape" -p "RightHandRing4";
	rename -uid "95B9A110-4796-2C4E-9392-AA99FC2EE3E7";
	setAttr -k off ".v";
createNode joint -n "RightHandThumb1" -p "RightHand";
	rename -uid "155F390D-462D-412F-C70B-2B97FCF9D7CC";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 3;
	setAttr ".t" -type "double3" -1.5000534057617188 1.7674713134765625 -2.9999790191650391 ;
	setAttr ".r" -type "double3" 88.174375001048176 -31.806142752728579 -21.391207454104432 ;
	setAttr ".s" -type "double3" 1.0000004768371582 0.99999982118606567 1.0000001192092896 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 88.174375001048176 -31.806142752728579 -21.391207454104432 ;
	setAttr ".bps" -type "matrix" 0.0039718041002735627 0.0074178313859965001 -0.0054037831627562066 0
		 -0.0023724438720856391 -0.0048580923693987326 -0.0084125311783099718 0 -0.0088654599513295473 0.0046232968157037257 -0.00016969946906055051 0
		 -0.58578211725792872 1.0487211842311894 -0.042938946904708633 1;
	setAttr ".radi" 0.010976429879665375;
	setAttr -k on ".MaxHandle" 109;
	setAttr ".fbxID" 5;
createNode joint -n "RightHandThumb2" -p "RightHandThumb1";
	rename -uid "129DCC2D-44E9-1DEF-5315-13AD13361E74";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 4;
	setAttr ".t" -type "double3" -5.2255592346191406 -0.11667633056640625 -0.0022125244140625 ;
	setAttr ".r" -type "double3" -0.16976961641965552 0.47321611593671892 -16.726784936685871 ;
	setAttr ".s" -type "double3" 1.0000003576278687 0.99999958276748657 1.0000001192092896 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.16976961641965552 0.47321611593671892 -16.726784936685871 ;
	setAttr ".bps" -type "matrix" 0.0045596274705660489 0.0084636964361481191 -0.0027524481412448802 0
		 -0.0011027797523626573 -0.0025315183838263517 -0.0096112176113422702 0 -0.0088314101073312581 0.0046858794073153173 -0.00022091810545999969 0
		 -0.60624059176015754 1.0105154621653836 -0.013719239163809467 1;
	setAttr ".radi" 0.0073082160204648982;
	setAttr -k on ".MaxHandle" 110;
	setAttr ".fbxID" 5;
createNode joint -n "RightHandThumb3" -p "RightHandThumb2";
	rename -uid "D4697905-470D-8584-B7C3-6EAAB732BBDB";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 5;
	setAttr ".t" -type "double3" -3.4800987243652344 0.0013523101806640625 4.57763671875e-05 ;
	setAttr ".r" -type "double3" 0.00024802109640244464 -3.4150962134509449e-06 -1.9636803227343334e-05 ;
	setAttr ".s" -type "double3" 0.99999946355819702 1.0000005960464478 0.99999994039535522 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 0.00024802109640244464 -3.4150962134509449e-06 -1.9636803227343334e-05 ;
	setAttr ".bps" -type "matrix" 0.0045596248761500119 0.0084636930427861006 -0.0027524433838634443 0
		 -0.0011028170762497542 -0.0025314967077938906 -0.0096112252396290572 0 -0.0088314050789414268 0.004685889581880303 -0.0002208763233378224 0
		 -0.62211044107421309 0.98105775409898333 -0.0041534553588344087 1;
	setAttr ".radi" 0.0064773266762495037;
	setAttr -k on ".MaxHandle" 111;
	setAttr ".fbxID" 5;
createNode transform -n "RightHandThumb4" -p "RightHandThumb3";
	rename -uid "8408F123-46D1-3711-B559-A7856528845B";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" -3.0831451416015625 0.089235305786132812 0.002227783203125 ;
	setAttr ".r" -type "double3" 0.00043585149836063077 -1.0245283755018989e-05 -4.2688682312579617e-06 ;
	setAttr ".s" -type "double3" 0.99999988079071045 0.99999994039535522 0.99999982118606567 ;
	setAttr -k on ".MaxHandle" 112;
createNode locator -n "RightHandThumb4Shape" -p "RightHandThumb4";
	rename -uid "921B0A9E-4448-897C-6EB9-56881CB1A4DC";
	setAttr -k off ".v";
createNode joint -n "RightHandMiddle1" -p "RightHand";
	rename -uid "3F79513E-4C17-1C00-811F-2492FDF2B0DF";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 3;
	setAttr ".t" -type "double3" -8.6899681091308594 -0.45590972900390625 -1.4039011001586914 ;
	setAttr ".r" -type "double3" -1.9729950280328199 -3.3453710961207199 -12.890760421912512 ;
	setAttr ".s" -type "double3" 1.0000002384185791 1 1.0000002384185791 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -1.9729950280328199 -3.3453710961207199 -12.890760421912512 ;
	setAttr ".bps" -type "matrix" 0.0060004747305448646 0.0079640534690534441 -0.00075389408410400747 0
		 0.0079961157373854772 -0.0059991329887483721 0.00026937414383202654 0 -0.00023773816196569409 -0.00076445699933179814 -0.0099679224309986349 0
		 -0.65535552206018544 1.0192946117825672 -0.057506068398318302 1;
	setAttr ".radi" 0.010681249871850014;
	setAttr -k on ".MaxHandle" 113;
	setAttr ".fbxID" 5;
createNode joint -n "RightHandMiddle2" -p "RightHandMiddle1";
	rename -uid "E3288B4A-4806-1568-3584-08A0DF2E050E";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 4;
	setAttr ".t" -type "double3" -5.0863037109375 -0.0035858154296875 -0.001979827880859375 ;
	setAttr ".r" -type "double3" -0.0001870831731560299 -2.1344343771442323e-06 -20.000021377216211 ;
	setAttr ".s" -type "double3" 1.0000001192092896 1 0.99999982118606567 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.0001870831731560299 -2.1344343771442323e-06 -20.000021377216211 ;
	setAttr ".bps" -type "matrix" 0.0029037659430888492 0.0095355887963325565 -0.00080056055597630196 0
		 0.0095661760403541081 -0.0029134682378119249 -4.6858187662071324e-06 0 -0.00023770699199139467 -0.00076446673097394023 -0.0099679206341253667 0
		 -0.68590396086408978 0.97881004234573277 -0.053652765275904436 1;
	setAttr ".radi" 0.0062937800958752631;
	setAttr -k on ".MaxHandle" 114;
	setAttr ".fbxID" 5;
createNode joint -n "RightHandMiddle3" -p "RightHandMiddle2";
	rename -uid "DC8CC68C-472D-DAF7-5428-45BCFDACA56B";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 5;
	setAttr ".t" -type "double3" -2.9970321655273438 0.00481414794921875 0.00014495849609375 ;
	setAttr ".r" -type "double3" 5.5495288557685801e-06 2.5613200817610839e-06 -9.9999984065621952 ;
	setAttr ".s" -type "double3" 1.0000002384185791 1 1 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 5.5495288557685801e-06 2.5613200817610839e-06 -9.9999984065621952 ;
	setAttr ".bps" -type "matrix" 0.0011985027494334673 0.0098966425863237055 -0.00078758430456012454 0
		 0.0099250779392540348 -0.0012133688405648289 -0.00014363145587255254 0 -0.00023770789973291613 -0.00076446617103586505 -0.0099679206554213733 0
		 -0.69456062226757143 0.95021743932279212 -0.051254927032200116 1;
	setAttr ".radi" 0.0049759772792458534;
	setAttr -k on ".MaxHandle" 115;
	setAttr ".fbxID" 5;
createNode transform -n "RightHandMiddle4" -p "RightHandMiddle3";
	rename -uid "23F9FF3A-42C9-B8D8-BF4A-F08E6556C47B";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" -2.3683624267578125 -0.0724945068359375 0.013855934143066406 ;
	setAttr ".r" -type "double3" 3.2016507917769653e-07 -3.8419809501323467e-06 -1.280660316710784e-06 ;
	setAttr ".s" -type "double3" 1.0000001192092896 1.0000001192092896 1.0000001192092896 ;
	setAttr -k on ".MaxHandle" 116;
createNode locator -n "RightHandMiddle4Shape" -p "RightHandMiddle4";
	rename -uid "449E7EAD-46ED-28B2-F334-05B79BA38CE4";
	setAttr -k off ".v";
createNode joint -n "RightHandIndex1" -p "RightHand";
	rename -uid "60F5D5BF-43A9-7E4F-9A20-D49776756B1B";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 3;
	setAttr ".t" -type "double3" -8.6192741394042969 -0.1528778076171875 -3.7471089363098145 ;
	setAttr ".r" -type "double3" 1.9977978552260773 -9.6467942559993691 -13.340862109687748 ;
	setAttr ".s" -type "double3" 1.0000004768371582 1.0000003576278687 0.9999997615814209 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 1.9977978552260773 -9.6467942559993691 -13.340862109687748 ;
	setAttr ".bps" -type "matrix" 0.0058459185037094954 0.0079011460966440759 -0.0018432001553274446 0
		 0.0079849942667443649 -0.0060054421286205454 -0.00041788741837995956 0 -0.0014370966338540026 -0.0012274966674629317 -0.0098197906972494389 0
		 -0.65248427395361164 1.0176462900184775 -0.03410124486595871 1;
	setAttr ".radi" 0.0093664096668362624;
	setAttr -k on ".MaxHandle" 117;
	setAttr ".fbxID" 5;
createNode joint -n "RightHandIndex2" -p "RightHandIndex1";
	rename -uid "D41142BF-4178-7B57-1B3D-C2AC370D263D";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 4;
	setAttr ".t" -type "double3" -4.4601898193359375 -0.00115966796875 3.62396240234375e-05 ;
	setAttr ".r" -type "double3" -0.00022454237297378412 -9.818395084982777e-06 -20.000020350762838 ;
	setAttr ".s" -type "double3" 1.0000002384185791 1.0000003576278687 1.0000002384185791 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.00022454237297378412 -9.818395084982777e-06 -20.000020350762838 ;
	setAttr ".bps" -type "matrix" 0.0027623346331101012 0.0094786339544443207 -0.0015891173680994755 0
		 0.0095028720855410333 -0.0029409114068744508 -0.0010230597511798694 0 -0.0014370602080718332 -0.0012275101098619507 -0.0098197967756035974 0
		 -0.67856749217044776 0.98241259847199669 -0.025880093553038039 1;
	setAttr ".radi" 0.0055639602430164825;
	setAttr -k on ".MaxHandle" 118;
	setAttr ".fbxID" 5;
createNode joint -n "RightHandIndex3" -p "RightHandIndex2";
	rename -uid "8DC03F4A-450C-E612-E943-1BAD5EFBE433";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 5;
	setAttr ".t" -type "double3" -2.6494903564453125 -0.00739288330078125 0.0002384185791015625 ;
	setAttr ".r" -type "double3" 6.8728824644180493e-05 -8.5377396639453417e-07 -10.000003841256706 ;
	setAttr ".s" -type "double3" 0.9999997615814209 0.99999946355819702 0.9999995231628418 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 6.8728824644180493e-05 -8.5377396639453417e-07 -10.000003841256706 ;
	setAttr ".bps" -type "matrix" 0.0010702112281098116 0.0098453138493011655 -0.0013873222263037068 0
		 0.0098381695511869996 -0.0012502849831418305 -0.0012834756936054557 0 -0.001437071324149886 -0.0012275080247681107 -0.0098197905535806537 0
		 -0.68595686738835138 0.95732049837103406 -0.021664520271642829 1;
	setAttr ".radi" 0.004546002745628358;
	setAttr -k on ".MaxHandle" 119;
	setAttr ".fbxID" 5;
createNode transform -n "RightHandIndex4" -p "RightHandIndex3";
	rename -uid "D91B377B-46D4-4AED-C6E1-76A27B2832B2";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" -2.1629180908203125 -0.08838653564453125 0.012761116027832031 ;
	setAttr ".r" -type "double3" 6.1951957591356569e-05 -4.2688667045922558e-06 -2.5613200227553589e-06 ;
	setAttr ".s" -type "double3" 1.0000003576278687 0.99999988079071045 0.99999988079071045 ;
	setAttr -k on ".MaxHandle" 120;
createNode locator -n "RightHandIndex4Shape" -p "RightHandIndex4";
	rename -uid "7D8DD560-42F6-1315-A267-AF90035A6C5F";
	setAttr -k off ".v";
createNode transform -n "RightHandPinky" -p "RightHand";
	rename -uid "9C73868A-4B04-709E-C9BC-42B991FA68DD";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" -3.4000167846679688 -4.57763671875e-05 -0.99995708465576172 ;
	setAttr ".r" -type "double3" -9.1433826878132903e-05 -8.028137446317008e-05 -3.5858480318570373e-05 ;
	setAttr ".s" -type "double3" 1.0000003576278687 0.99999994039535522 1.0000002384185791 ;
	setAttr -k on ".MaxHandle" 121;
createNode locator -n "RightHandPinkyShape" -p "RightHandPinky";
	rename -uid "04F481F6-425E-F838-3EE4-938CA30C7CD8";
	setAttr -k off ".v";
createNode joint -n "RightHandPinky1" -p "RightHandPinky";
	rename -uid "44BD38F3-40B1-6A67-4EB8-A489429D8C26";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 4;
	setAttr ".t" -type "double3" -4.1256446838378906 0.2577667236328125 3.9289617538452148 ;
	setAttr ".r" -type "double3" -10.441826716705179 8.0233670772388184 -14.640199700928211 ;
	setAttr ".s" -type "double3" 0.9999997615814209 1.0000001192092896 1.0000001192092896 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -10.441826716705179 8.0233670772388184 -14.640199700928211 ;
	setAttr ".bps" -type "matrix" 0.0057397260964980514 0.0080960396044096172 0.0012287598393615205 0
		 0.0079110695181375482 -0.0058697536306208066 0.0017207623717463345 0 0.0021143856631409899 -1.5586220243668541e-05 -0.0097739216914648902 0
		 -0.64255552951785533 1.0209330490413826 -0.10106491285001987 1;
	setAttr ".radi" 0.0078045258298516272;
	setAttr -k on ".MaxHandle" 122;
	setAttr ".fbxID" 5;
createNode joint -n "RightHandPinky2" -p "RightHandPinky1";
	rename -uid "E70377A2-42E7-39C1-E9BB-C286882C0D6E";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 5;
	setAttr ".t" -type "double3" -3.7164306640625 3.0517578125e-05 1.2874603271484375e-05 ;
	setAttr ".r" -type "double3" -2.8194455566874255 -1.0255919706264838 -19.962373432072052 ;
	setAttr ".s" -type "double3" 0.99999982118606567 1.0000001192092896 0.9999997615814209 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -2.8194455566874255 -1.0255919706264838 -19.962373432072052 ;
	setAttr ".bps" -type "matrix" 0.0027314170007362759 0.0096117359759090686 0.00039242450557346162 0
		 0.0092823210894764415 -0.0027405065700807385 0.0025156003537711974 0 0.0025254691661487161 -0.00032284959448718951 -0.0096704774360951568 0
		 -0.66388655493764182 0.99084449986675882 -0.1056315869176556 1;
	setAttr ".radi" 0.0043452554941177382;
	setAttr -k on ".MaxHandle" 123;
	setAttr ".fbxID" 5;
createNode joint -n "RightHandPinky3" -p "RightHandPinky2";
	rename -uid "90489569-4648-3BE6-8FB3-968B0423D1F6";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 6;
	setAttr ".t" -type "double3" -2.0691680908203125 0.0008697509765625 0.00011730194091796875 ;
	setAttr ".r" -type "double3" -2.9545974610668195 -0.52005068150659406 -9.9989894871513929 ;
	setAttr ".s" -type "double3" 0.99999958276748657 0.99999970197677612 0.9999997615814209 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -2.9545974610668195 -0.52005068150659406 -9.9989894871513929 ;
	setAttr ".bps" -type "matrix" 0.0011011095617768814 0.0099382339210980723 -0.00013809351432084443 0
		 0.0094731389592211512 -0.0010073259824074274 0.0030405595638005123 0 0.0030078655764860848 -0.00046561181203949727 -0.0095255579837602074 0
		 -0.6695299462880222 0.97095378105886843 -0.10644252560255267 1;
	setAttr ".radi" 0.0043451870419085039;
	setAttr -k on ".MaxHandle" 124;
	setAttr ".fbxID" 5;
createNode transform -n "RightHandPinky4" -p "RightHandPinky3";
	rename -uid "9428F0BC-4310-3A93-776D-9994E413A7B7";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" -2.0678863525390625 -0.07086181640625 0.012101173400878906 ;
	setAttr ".r" -type "double3" 1.1392540734073798e-05 2.0917455579940631e-05 -4.268868485702359e-07 ;
	setAttr ".s" -type "double3" 1 1.0000001192092896 1.0000004768371582 ;
	setAttr -k on ".MaxHandle" 125;
createNode locator -n "RightHandPinky4Shape" -p "RightHandPinky4";
	rename -uid "94462207-4B2B-EC4E-EE78-7B9B6667FF6E";
	setAttr -k off ".v";
createNode transform -n "RightHand_Dummy" -p "RightHand";
	rename -uid "5D68C311-4A14-4487-2E84-56B0E0A0A4EF";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 51.784587860107422 4.8100357055664062 -29.323467254638672 ;
	setAttr ".r" -type "double3" -150.44717262289311 -88.933844119448935 10.532211212672459 ;
	setAttr ".s" -type "double3" 1.000001072883606 1.0000011920928955 0.99999886751174927 ;
	setAttr -k on ".MaxHandle" 126;
createNode locator -n "RightHand_DummyShape" -p "RightHand_Dummy";
	rename -uid "BF411E22-4983-2A60-4BDA-CCA554E96641";
	setAttr -k off ".v";
createNode transform -n "Weapon_Root" -p "RightHand_Dummy";
	rename -uid "40899872-42EF-2484-24E2-61BA1C57FC92";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".r" -type "double3" 1.0422034125799949e-10 5.9916687120282509e-11 1.516486121991773e-10 ;
	setAttr ".s" -type "double3" 1.0000015497207642 1.0000007152557373 0.99999904632568359 ;
	setAttr -k on ".MaxHandle" 127;
createNode locator -n "Weapon_RootShape" -p "Weapon_Root";
	rename -uid "C3F3F913-4397-0342-DFA8-BB838001D600";
	setAttr -k off ".v";
createNode transform -n "Bullet" -p "Weapon_Root";
	rename -uid "BE2A8C66-4915-60B7-2944-59B67F0BD170";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".r" -type "double3" -7.8165335146732563e-11 1.0892407159150708e-12 2.6462218104318678e-12 ;
	setAttr ".s" -type "double3" 0.99999988079071045 0.99999970197677612 0.99999982118606567 ;
	setAttr -k on ".MaxHandle" 128;
createNode locator -n "BulletShape" -p "Bullet";
	rename -uid "700E622A-45CA-E6AE-67E1-2CBB66B5294A";
	setAttr -k off ".v";
createNode transform -n "Trigger" -p "Weapon_Root";
	rename -uid "C9CA719B-44B8-CA25-08D7-D18E49E41903";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".r" -type "double3" -7.8165335146732563e-11 1.0892407159150708e-12 2.6462218104318678e-12 ;
	setAttr ".s" -type "double3" 0.99999988079071045 0.99999970197677612 0.99999982118606567 ;
	setAttr -k on ".MaxHandle" 129;
createNode locator -n "TriggerShape" -p "Trigger";
	rename -uid "011B0F5B-46B2-F1D0-8C18-47B6D0146CDC";
	setAttr -k off ".v";
createNode transform -n "Magazine" -p "Weapon_Root";
	rename -uid "9C0B3FE6-40BE-3032-5E35-DAB2EEFECD52";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".t" -type "double3" -6.5897769927978516 3.3101348876953125 -0.0031862258911132812 ;
	setAttr ".r" -type "double3" 0.00023809846218699493 7.031215986292635e-05 -11.099504477546935 ;
	setAttr ".s" -type "double3" 0.99999994039535522 0.9999997615814209 0.9999997615814209 ;
	setAttr -k on ".MaxHandle" 130;
createNode locator -n "MagazineShape" -p "Magazine";
	rename -uid "E640BE87-437D-263C-EF9C-69B74302EE7C";
	setAttr -k off ".v";
createNode transform -n "Bolt" -p "Weapon_Root";
	rename -uid "B2578785-4CFF-283B-1314-76A02500629D";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".t" -type "double3" -6.9570732116699219 8.6678924560546875 -3.145965576171875 ;
	setAttr ".r" -type "double3" -1.302755585778876e-10 1.6225432674740981e-10 2.6462218104318678e-12 ;
	setAttr ".s" -type "double3" 0.99999988079071045 0.99999970197677612 0.99999982118606567 ;
	setAttr -k on ".MaxHandle" 131;
createNode locator -n "BoltShape" -p "Bolt";
	rename -uid "42638C90-4D37-4EBB-51C8-22A915B424C0";
	setAttr -k off ".v";
createNode transform -n "Bullets_Magazine" -p "Weapon_Root";
	rename -uid "3C650BE2-471D-79E3-C8E1-D08E26A1A29E";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".r" -type "double3" -7.8165335146732563e-11 1.0892407159150708e-12 2.6462218104318678e-12 ;
	setAttr ".s" -type "double3" 0.99999988079071045 0.99999970197677612 0.99999982118606567 ;
	setAttr -k on ".MaxHandle" 132;
createNode locator -n "Bullets_MagazineShape" -p "Bullets_Magazine";
	rename -uid "9CCA84D4-43F5-112E-4742-6EBB1850D3A3";
	setAttr -k off ".v";
createNode transform -n "Bullets_holder" -p "Weapon_Root";
	rename -uid "7AB03183-4AC3-8CEA-09AA-C39999ABDA78";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".r" -type "double3" -7.8165335146732563e-11 1.0892407159150708e-12 2.6462218104318678e-12 ;
	setAttr ".s" -type "double3" 0.99999988079071045 0.99999970197677612 0.99999982118606567 ;
	setAttr -k on ".MaxHandle" 133;
createNode locator -n "Bullets_holderShape" -p "Bullets_holder";
	rename -uid "E7E6E0DB-44CC-3D79-09EC-B988D2A8EA61";
	setAttr -k off ".v";
createNode transform -n "Bullets_on_holder" -p "Weapon_Root";
	rename -uid "1505EFC7-4F08-C501-B0CC-C089F0B6323A";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".r" -type "double3" -2.6055111715577521e-11 5.9663001186494963e-11 1.5246308738565147e-10 ;
	setAttr ".s" -type "double3" 0.99999988079071045 0.99999970197677612 0.99999982118606567 ;
	setAttr -k on ".MaxHandle" 134;
createNode locator -n "Bullets_on_holderShape" -p "Bullets_on_holder";
	rename -uid "08797D72-4BB7-6478-04E3-D6A0F9916B0C";
	setAttr -k off ".v";
createNode transform -n "Universal1" -p "Weapon_Root";
	rename -uid "276EFA1A-4BCC-452F-7F1B-C7AC73C0AF5E";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".r" -type "double3" -7.8165335146732563e-11 1.0892407159150708e-12 2.6462218104318678e-12 ;
	setAttr ".s" -type "double3" 0.99999988079071045 0.99999970197677612 0.99999982118606567 ;
	setAttr -k on ".MaxHandle" 135;
createNode locator -n "Universal1Shape" -p "Universal1";
	rename -uid "2EA7C421-4156-5960-3116-11BF39F0903B";
	setAttr -k off ".v";
createNode transform -n "Universal2" -p "Weapon_Root";
	rename -uid "0B382BD7-4561-114D-5037-168B508FD4EC";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".r" -type "double3" -7.8165335146732563e-11 1.0892407159150708e-12 2.6462218104318678e-12 ;
	setAttr ".s" -type "double3" 0.99999988079071045 0.99999970197677612 0.99999982118606567 ;
	setAttr -k on ".MaxHandle" 136;
createNode locator -n "Universal2Shape" -p "Universal2";
	rename -uid "97069D36-4355-0D89-1A3A-A59FB964B189";
	setAttr -k off ".v";
createNode joint -n "RightWristExtra" -p "RightForeArmRoll";
	rename -uid "214A1B57-4224-EE5F-AA99-F3A541F57B6F";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 2;
	setAttr ".t" -type "double3" -6.1000137329101562 3.814697265625e-05 -1.9073486328125e-06 ;
	setAttr ".r" -type "double3" 2.6680416903702044e-08 1.291331408445895e-05 1.0245273984364353e-05 ;
	setAttr ".s" -type "double3" 1.0000009536743164 1.0000003576278687 0.9999997615814209 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 2.6680416903702044e-08 1.291331408445895e-05 1.0245273984364353e-05 ;
	setAttr ".bps" -type "matrix" 0.0076494515975663296 0.0064383777280206779 -0.00018293960823900939 0
		 0.0064389323727249478 -0.0076510816894779779 -3.4010772170095288e-05 0 -0.00016186361527371126 -9.177534186189511e-05 -0.0099982801474774799 0
		 -0.57852371368607924 1.0780652089607077 -0.073330897170007847 1;
	setAttr ".radi" 0.012810030654072763;
	setAttr -k on ".MaxHandle" 137;
	setAttr ".fbxID" 5;
createNode joint -n "RightForeArmExtra" -p "RightForeArm";
	rename -uid "3A7C0F7A-41DF-D0AD-D6FC-C9BF03501793";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" -12.400020599365234 -7.62939453125e-06 -3.337860107421875e-06 ;
	setAttr ".r" -type "double3" -0.00010653491739630559 2.6680401000949015e-08 -5.1226369921822182e-06 ;
	setAttr ".s" -type "double3" 1.0000008344650269 1.0000002384185791 0.99999982118606567 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.00010653491739630559 2.6680401000949015e-08 -5.1226369921822182e-06 ;
	setAttr ".bps" -type "matrix" 0.0076494488453259157 0.0064383789484652176 -0.0001829465749970327 0
		 0.0064389341239420245 -0.0076510801329466391 -3.4029383981684098e-05 0 -0.00016188097173906881 -9.1765670424890354e-05 -0.0099982829359969699 0
		 -0.4706671843235492 1.168846444875471 -0.075910390147982731 1;
	setAttr ".radi" 0.026040055900812153;
	setAttr -k on ".MaxHandle" 138;
	setAttr ".fbxID" 5;
createNode joint -n "RightElbowExtra" -p "RightArmRoll";
	rename -uid "113FB4B3-4E86-4437-95C0-75B731FD24B8";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".t" -type "double3" -9.5000190734863281 -4.57763671875e-05 -7.62939453125e-06 ;
	setAttr ".r" -type "double3" 0.0001067384650431689 -7.3228646538326894 1.0329528325799959e-05 ;
	setAttr ".s" -type "double3" 1.0000005960464478 1.0000005960464478 0.9999995231628418 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 0.0001067384650431689 -7.3228646538326894 1.0329528325799959e-05 ;
	setAttr ".bps" -type "matrix" 0.0076076927767025895 0.0063975493772944741 0.0010929365424163671 0
		 0.0064389274524853058 -0.0076510888573380811 -3.403079120537411e-05 0 0.00081444350919605271 0.00072962336046224945 -0.0099400448742895491 0
		 -0.3795346060638406 1.2455562185457689 -0.079354410900141517 1;
	setAttr ".radi" 0.01995002947747708;
	setAttr -k on ".MaxHandle" 139;
	setAttr ".fbxID" 5;
createNode transform -n "RightHandIK_Helper" -p "Spine3";
	rename -uid "1A4D8233-4F8A-6925-E2AA-85AEE5E5A12A";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" 19.486648559570312 15.999979019165039 2.0111968517303467 ;
	setAttr ".r" -type "double3" 1.6450914835773969e-05 9.2084648495569942e-05 -89.999920542207562 ;
	setAttr ".s" -type "double3" 0.99999904632568359 0.99999982118606567 0.99999856948852539 ;
	setAttr -k on ".MaxHandle" 140;
createNode locator -n "RightHandIK_HelperShape" -p "RightHandIK_Helper";
	rename -uid "D1F93419-4A57-900C-EC85-15A44FB36132";
	setAttr -k off ".v";
createNode transform -n "RightHandIK" -p "RightHandIK_Helper";
	rename -uid "1F4ECD42-4204-4AA4-3006-0F9762196E8E";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" -42.617347717285156 -35.837394714355469 -6.3147735595703125 ;
	setAttr ".r" -type "double3" -179.80511240863618 1.0481985174973409 40.086601194804004 ;
	setAttr ".s" -type "double3" 1.0000002384185791 1.0000004768371582 1.0000001192092896 ;
	setAttr -k on ".MaxHandle" 141;
createNode locator -n "RightHandIKShape" -p "RightHandIK";
	rename -uid "E90E68F6-4F05-4E86-767D-D2A256943852";
	setAttr -k off ".v";
createNode transform -n "RightAimIK_Helper" -p "RightHandIK_Helper";
	rename -uid "DB2DA4D8-4137-8F8D-257A-0A9E35198A80";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".r" -type "double3" 8.1422204698607617e-13 8.5915975737205698e-13 -1.6284439969093206e-12 ;
	setAttr ".s" -type "double3" 1 0.99999994039535522 0.99999994039535522 ;
	setAttr -k on ".MaxHandle" 142;
createNode locator -n "RightAimIK_HelperShape" -p "RightAimIK_Helper";
	rename -uid "792ECB09-4CB7-2F7D-E73F-01B5767EBCA3";
	setAttr -k off ".v";
createNode transform -n "Marker" -p "RightAimIK_Helper";
	rename -uid "F5811839-4E88-24D9-7503-389F93B37C0F";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" -1.1444091796875e-05 9.1552734375e-05 20.997812271118164 ;
	setAttr ".r" -type "double3" 8.1422204698607617e-13 2.4849328815377007e-13 0 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 1 ;
	setAttr -k on ".MaxHandle" 143;
createNode locator -n "MarkerShape" -p "Marker";
	rename -uid "45D5415B-4059-03A7-ABA7-1ABAD5A3CFEA";
	setAttr -k off ".v";
createNode transform -n "LeftHandIK" -p "RightHandIK_Helper";
	rename -uid "732B3E7F-4BEA-2D70-61D8-82BC9BF3DC29";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" 74.617393493652344 -35.837234497070312 -6.3146805763244629 ;
	setAttr ".r" -type "double3" 0.19507034937391532 -1.0481623035842007 -40.08628767072463 ;
	setAttr ".s" -type "double3" 1.0000001192092896 1.0000002384185791 1.0000001192092896 ;
	setAttr -k on ".MaxHandle" 144;
createNode locator -n "LeftHandIKShape" -p "LeftHandIK";
	rename -uid "4E5C4E3A-4F6D-29C4-1CC4-50B99ADD3193";
	setAttr -k off ".v";
createNode transform -n "Weapon_Holster" -p "Spine3";
	rename -uid "A77501D7-4838-48B2-6D7D-49904F6F9EBC";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".t" -type "double3" -5.01849365234375 -16.255071640014648 -3.4002671241760254 ;
	setAttr ".r" -type "double3" -97.999998388860448 -1.9999972397835108 179.99999499103518 ;
	setAttr ".s" -type "double3" 0.99999904632568359 1 0.99999892711639404 ;
	setAttr -k on ".MaxHandle" 145;
createNode locator -n "Weapon_HolsterShape" -p "Weapon_Holster";
	rename -uid "83907A34-4BEB-7A33-5998-709C8929BA4D";
	setAttr -k off ".v";
createNode transform -n "Pistol_Holster" -p "Spine3";
	rename -uid "A15B5635-4AC7-A3FF-8DBF-CB9C594124A9";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".t" -type "double3" -1.5179824829101562 7.6052727699279785 20.019441604614258 ;
	setAttr ".r" -type "double3" 163.62458603182455 -1.0696053844221747 56.205915143067969 ;
	setAttr ".s" -type "double3" 0.99999916553497314 1 0.99999898672103882 ;
	setAttr -k on ".MaxHandle" 146;
createNode locator -n "Pistol_HolsterShape" -p "Pistol_Holster";
	rename -uid "3E0798BB-4F3C-2B89-F2F1-63AC45F01D94";
	setAttr -k off ".v";
createNode transform -n "Weapon2hnd_Holster" -p "Spine2";
	rename -uid "8A0F1256-49F5-FD90-8BCA-749866CCFB13";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".v" no;
	setAttr ".t" -type "double3" 47.085609436035156 14.25633716583252 -5.4795293807983398 ;
	setAttr ".r" -type "double3" -50.610031296170483 74.845314026197556 39.418922417122324 ;
	setAttr ".s" -type "double3" 0.99999880790710449 0.9999997615814209 0.99999839067459106 ;
	setAttr -k on ".MaxHandle" 147;
createNode locator -n "Weapon2hnd_HolsterShape" -p "Weapon2hnd_Holster";
	rename -uid "33D28FA5-4F70-2B7E-6710-D8BC90C8A4E8";
	setAttr -k off ".v";
createNode transform -n "weapon" -p "Pelvis";
	rename -uid "18CE6290-4BBA-D643-18F2-73B88A469913";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032useFBXASC032globalFBXASC032settings" 
		-ln "mrFBXASC032displacementFBXASC032useFBXASC032globalFBXASC032settings" -min 0 
		-max 1 -at "bool";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032viewFBXASC032dependent" 
		-ln "mrFBXASC032displacementFBXASC032viewFBXASC032dependent" -min 0 -max 1 -at "bool";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032method" -ln "mrFBXASC032displacementFBXASC032method" 
		-smn 0 -smx 100 -at "long";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032smoothingFBXASC032on" 
		-ln "mrFBXASC032displacementFBXASC032smoothingFBXASC032on" -min 0 -max 1 -at "bool";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032edgeFBXASC032length" 
		-ln "mrFBXASC032displacementFBXASC032edgeFBXASC032length" -smn 0 -smx 100 -at "double";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032maxFBXASC032displace" 
		-ln "mrFBXASC032displacementFBXASC032maxFBXASC032displace" -smn 0 -smx 100 -at "double";
	addAttr -is true -ci true -k true -sn "mrFBXASC032displacementFBXASC032parametricFBXASC032subdivisionFBXASC032level" 
		-ln "mrFBXASC032displacementFBXASC032parametricFBXASC032subdivisionFBXASC032level" 
		-smn 0 -smx 100 -at "long";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 0 
		-smx 0 -at "long";
	setAttr ".t" -type "double3" 36.233165386464449 14.035271587274222 21.171427673858705 ;
	setAttr ".r" -type "double3" 102.84637417701555 68.695967338534672 28.604366490759851 ;
	setAttr ".s" -type "double3" 1.0000002384185791 1.0000003576278687 1 ;
	setAttr -k on ".mrFBXASC032displacementFBXASC032useFBXASC032globalFBXASC032settings" 
		yes;
	setAttr -k on ".mrFBXASC032displacementFBXASC032viewFBXASC032dependent" yes;
	setAttr -k on ".mrFBXASC032displacementFBXASC032method" 6;
	setAttr -k on ".mrFBXASC032displacementFBXASC032smoothingFBXASC032on" yes;
	setAttr -k on ".mrFBXASC032displacementFBXASC032edgeFBXASC032length" 2;
	setAttr -k on ".mrFBXASC032displacementFBXASC032maxFBXASC032displace" 20;
	setAttr -k on ".mrFBXASC032displacementFBXASC032parametricFBXASC032subdivisionFBXASC032level" 
		5;
	setAttr -k on ".MaxHandle" 148;
createNode locator -n "weaponShape" -p "weapon";
	rename -uid "CA94560E-40FF-3312-A44D-C9BFE243304C";
	setAttr -k off ".v";
createNode joint -n "RightHipExtra" -p "Pelvis";
	rename -uid "7A6A7304-4F9D-A9DE-5573-2CA27CB35EFD";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" -8.130817767832383 8.9020757101990267 -2.1154885820921985 ;
	setAttr ".r" -type "double3" 179.98883082051177 -0.59110249132785841 -2.1123210577017537 ;
	setAttr ".s" -type "double3" 1 1 0.99999982118606567 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" 179.98883082051177 -0.59110249132785841 -2.1123210577017537 ;
	setAttr ".bps" -type "matrix" 0.00036856706724716301 0.0099926728639375944 0.00010316433937287815 0
		 0.0099932037399429324 -0.00036860658336581323 1.930979715992989e-06 0 5.73226943014089e-06 0.00010302304053232959 -0.0099994656437940553 0
		 -0.10299995087374063 0.91838318503748706 -0.022469726942590185 1;
	setAttr ".radi" 0.02799795806407929;
	setAttr -k on ".MaxHandle" 149;
	setAttr ".fbxID" 5;
createNode joint -n "LeftHipExtra" -p "Pelvis";
	rename -uid "D7718B78-4294-5B14-96A4-399BB1D33875";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	addAttr -ci true -h true -sn "fbxID" -ln "filmboxTypeID" -at "short";
	addAttr -ci true -sn "liw" -ln "lockInfluenceWeights" -min 0 -max 1 -at "bool";
	setAttr ".uoc" 1;
	setAttr ".oc" 1;
	setAttr ".t" -type "double3" -8.1308330266214455 -11.69790082941279 -2.1154637865599719 ;
	setAttr ".r" -type "double3" -0.010596820406139497 0.5911301172734732 -177.88764592825692 ;
	setAttr ".s" -type "double3" 0.99999994039535522 1 0.99999958276748657 ;
	setAttr ".ssc" no;
	setAttr ".pa" -type "double3" -0.010596820406139497 0.5911301172734732 -177.88764592825692 ;
	setAttr ".bps" -type "matrix" 0.00036857154969848009 -0.0099926720384684448 -0.00010317050493170072 0
		 0.0099932036097300572 0.0003686104395720114 -1.8677016348174843e-06 0 5.6693036068353513e-06 -0.0001030315135171494 0.0099994632080792466 0
		 0.10299980991837737 0.91838302344506428 -0.022469856348063678 1;
	setAttr ".radi" 0.027997964322566991;
	setAttr -k on ".MaxHandle" 150;
	setAttr ".fbxID" 5;
createNode transform -n "LeftHip_Helper" -p "Pelvis";
	rename -uid "FFA3CC73-4129-3FCB-51BF-05A5F291E7A7";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" 0.03086436107385282 -11.6979246712707 -1.8684800200041902 ;
	setAttr ".r" -type "double3" 0.00029301489131707952 -8.4809485492330139e-06 -179.99997768820188 ;
	setAttr -k on ".MaxHandle" 151;
createNode locator -n "LeftHip_HelperShape" -p "LeftHip_Helper";
	rename -uid "02234CD0-44CD-4D18-77C6-728CC504E319";
	setAttr -k off ".v";
createNode transform -n "RightHip_Helper" -p "Pelvis";
	rename -uid "9209ED25-42E6-4B26-00F0-EBB99F1B9942";
	addAttr -is true -ci true -h true -k true -sn "MaxHandle" -ln "MaxHandle" -smn 
		0 -smx 0 -at "long";
	setAttr ".t" -type "double3" 0.03086436107385282 8.902071895501761 -1.8685145906981555 ;
	setAttr ".r" -type "double3" 179.99971814101832 2.8117694373920103e-05 5.1225889530796498e-06 ;
	setAttr -k on ".MaxHandle" 152;
createNode locator -n "RightHip_HelperShape" -p "RightHip_Helper";
	rename -uid "64C25B3B-4AE3-AD33-716C-948741FE096F";
	setAttr -k off ".v";
select -ne :time1;
	setAttr ".o" 1;
	setAttr ".unw" 1;
select -ne :hardwareRenderingGlobals;
	setAttr ".otfna" -type "stringArray" 22 "NURBS Curves" "NURBS Surfaces" "Polygons" "Subdiv Surface" "Particles" "Particle Instance" "Fluids" "Strokes" "Image Planes" "UI" "Lights" "Cameras" "Locators" "Joints" "IK Handles" "Deformers" "Motion Trails" "Components" "Hair Systems" "Follicles" "Misc. UI" "Ornaments"  ;
	setAttr ".otfva" -type "Int32Array" 22 0 1 1 1 1 1
		 1 1 1 0 0 0 0 0 0 0 0 0
		 0 0 0 0 ;
	setAttr ".fprt" yes;
	setAttr ".rtfm" 1;
select -ne :renderPartition;
	setAttr -s 41 ".st";
select -ne :renderGlobalsList1;
select -ne :defaultShaderList1;
	setAttr -s 45 ".s";
select -ne :postProcessList1;
	setAttr -s 2 ".p";
select -ne :defaultRenderUtilityList1;
	setAttr -s 34 ".u";
select -ne :defaultRenderingList1;
select -ne :defaultTextureList1;
	setAttr -s 34 ".tx";
select -ne :standardSurface1;
	setAttr ".bc" -type "float3" 0.40000001 0.40000001 0.40000001 ;
	setAttr ".sr" 0.5;
select -ne :openPBR_shader1;
	setAttr ".bc" -type "float3" 0.40000001 0.40000001 0.40000001 ;
	setAttr ".sr" 0.5;
select -ne :initialShadingGroup;
	setAttr ".ro" yes;
select -ne :initialParticleSE;
	setAttr ".ro" yes;
select -ne :defaultRenderGlobals;
	addAttr -ci true -h true -sn "dss" -ln "defaultSurfaceShader" -dt "string";
	setAttr ".ren" -type "string" "arnold";
	setAttr ".dss" -type "string" "openPBR_shader1";
select -ne :defaultResolution;
	setAttr ".pa" 1;
select -ne :defaultColorMgtGlobals;
	setAttr ".cfe" yes;
	setAttr ".cfp" -type "string" "<MAYA_RESOURCES>/OCIO-configs/Maya2022-default/config.ocio";
	setAttr ".vtn" -type "string" "ACES 1.0 SDR-video (sRGB)";
	setAttr ".vn" -type "string" "ACES 1.0 SDR-video";
	setAttr ".dn" -type "string" "sRGB";
	setAttr ".wsn" -type "string" "ACEScg";
	setAttr ".otn" -type "string" "ACES 1.0 SDR-video (sRGB)";
	setAttr ".potn" -type "string" "ACES 1.0 SDR-video (sRGB)";
select -ne :hardwareRenderGlobals;
	setAttr ".ctrs" 256;
	setAttr ".btrs" 512;
connectAttr "Pelvis.s" "LeftUpLeg.is";
connectAttr "LeftUpLeg.s" "LeftUpLegRoll.is";
connectAttr "LeftUpLegRoll.s" "LeftKneeExtra.is";
connectAttr "LeftUpLegRoll.s" "LeftLeg.is";
connectAttr "LeftLeg.s" "LeftLegRoll.is";
connectAttr "LeftLegRoll.s" "LeftFoot.is";
connectAttr "LeftFoot.s" "LeftToeBase.is";
connectAttr "Pelvis.s" "RightUpLeg.is";
connectAttr "RightUpLeg.s" "RightUpLegRoll.is";
connectAttr "RightUpLegRoll.s" "RightKneeExtra.is";
connectAttr "RightUpLegRoll.s" "RightLeg.is";
connectAttr "RightLeg.s" "RightLegRoll.is";
connectAttr "RightLegRoll.s" "RightFoot.is";
connectAttr "RightFoot.s" "RightToeBase.is";
connectAttr "Pelvis.s" "Spine.is";
connectAttr "Spine.s" "Spine1.is";
connectAttr "Spine1.s" "Spine2.is";
connectAttr "Spine2.s" "Spine3.is";
connectAttr "Spine3.s" "Neck.is";
connectAttr "Neck.s" "Neck1.is";
connectAttr "Neck1.s" "Head.is";
connectAttr "Face_Hub.s" "Face_EyelidUpperLeft.is";
connectAttr "Face_Hub.s" "Face_EyelidUpperRight.is";
connectAttr "Face_Hub.s" "Face_Jawbone.is";
connectAttr "Face_Jawbone.s" "Face_Chin.is";
connectAttr "Face_Jawbone.s" "Face_ChopLeft.is";
connectAttr "Face_Jawbone.s" "Face_ChopRight.is";
connectAttr "Face_Jawbone.s" "Face_Jowl.is";
connectAttr "Face_Jawbone.s" "Face_LipLowerLeft.is";
connectAttr "Face_Jawbone.s" "Face_LipLowerMiddle.is";
connectAttr "Face_Jawbone.s" "Face_LipLowerRight.is";
connectAttr "Face_Jawbone.s" "Face_Tongue.is";
connectAttr "Face_Hub.s" "EyeRight.is";
connectAttr "Face_Hub.s" "EyeLeft.is";
connectAttr "Face_Hub.s" "Face_CheekFrontLeft.is";
connectAttr "Face_Hub.s" "Face_CheekFrontRight.is";
connectAttr "Face_Hub.s" "Face_CheekUpperLeft.is";
connectAttr "Face_Hub.s" "Face_CheekUpperRight.is";
connectAttr "Face_Hub.s" "Face_CornerLeft.is";
connectAttr "Face_CornerLeft.s" "Face_CheekSideLeft.is";
connectAttr "Face_Hub.s" "Face_CornerRight.is";
connectAttr "Face_CornerRight.s" "Face_CheekSideRight.is";
connectAttr "Face_Hub.s" "Face_EyelidLowerLeft.is";
connectAttr "Face_Hub.s" "Face_EyelidLowerRight.is";
connectAttr "Face_Hub.s" "Face_Eyelids.is";
connectAttr "Face_Hub.s" "Face_Forehead.is";
connectAttr "Face_Forehead.s" "Face_BrowFrontLeft.is";
connectAttr "Face_Forehead.s" "Face_BrowFrontRight.is";
connectAttr "Face_Forehead.s" "Face_BrowMiddle.is";
connectAttr "Face_Forehead.s" "Face_BrowSideLeft.is";
connectAttr "Face_Forehead.s" "Face_BrowSideRight.is";
connectAttr "Face_Hub.s" "Face_LipUpperLeft.is";
connectAttr "Face_Hub.s" "Face_LipUpperMiddle.is";
connectAttr "Face_Hub.s" "Face_LipUpperRight.is";
connectAttr "Face_Hub.s" "Face_NostrilLeft.is";
connectAttr "Face_Hub.s" "Face_NostrilRight.is";
connectAttr "Spine3.s" "LeftShoulder.is";
connectAttr "LeftShoulder.s" "LeftArm.is";
connectAttr "LeftArm.s" "LeftArmRoll.is";
connectAttr "LeftArmRoll.s" "LeftForeArm.is";
connectAttr "LeftForeArm.s" "LeftForeArmRoll.is";
connectAttr "LeftForeArmRoll.s" "LeftHand.is";
connectAttr "LeftHand.s" "LeftHandRing.is";
connectAttr "LeftHandRing.s" "LeftHandRing1.is";
connectAttr "LeftHandRing1.s" "LeftHandRing2.is";
connectAttr "LeftHandRing2.s" "LeftHandRing3.is";
connectAttr "LeftHand.s" "LeftHandMiddle1.is";
connectAttr "LeftHandMiddle1.s" "LeftHandMiddle2.is";
connectAttr "LeftHandMiddle2.s" "LeftHandMiddle3.is";
connectAttr "LeftHand.s" "LeftHandIndex1.is";
connectAttr "LeftHandIndex1.s" "LeftHandIndex2.is";
connectAttr "LeftHandIndex2.s" "LeftHandIndex3.is";
connectAttr "LeftHand.s" "LeftHandThumb1.is";
connectAttr "LeftHandThumb1.s" "LeftHandThumb2.is";
connectAttr "LeftHandThumb2.s" "LeftHandThumb3.is";
connectAttr "LeftHandPinky.s" "LeftHandPinky1.is";
connectAttr "LeftHandPinky1.s" "LeftHandPinky2.is";
connectAttr "LeftHandPinky2.s" "LeftHandPinky3.is";
connectAttr "LeftForeArmRoll.s" "LeftWristExtra.is";
connectAttr "LeftForeArm.s" "LeftForeArmExtra.is";
connectAttr "LeftArmRoll.s" "LeftElbowExtra.is";
connectAttr "LeftArm.s" "LeftArmExtra.is";
connectAttr "Spine3.s" "RightShoulder.is";
connectAttr "RightShoulder.s" "RightArm.is";
connectAttr "RightArm.s" "RightArmExtra.is";
connectAttr "RightArm.s" "RightArmRoll.is";
connectAttr "RightArmRoll.s" "RightForeArm.is";
connectAttr "RightForeArm.s" "RightForeArmRoll.is";
connectAttr "RightForeArmRoll.s" "RightHand.is";
connectAttr "RightHand.s" "RightHandRing.is";
connectAttr "RightHandRing.s" "RightHandRing1.is";
connectAttr "RightHandRing1.s" "RightHandRing2.is";
connectAttr "RightHandRing2.s" "RightHandRing3.is";
connectAttr "RightHand.s" "RightHandThumb1.is";
connectAttr "RightHandThumb1.s" "RightHandThumb2.is";
connectAttr "RightHandThumb2.s" "RightHandThumb3.is";
connectAttr "RightHand.s" "RightHandMiddle1.is";
connectAttr "RightHandMiddle1.s" "RightHandMiddle2.is";
connectAttr "RightHandMiddle2.s" "RightHandMiddle3.is";
connectAttr "RightHand.s" "RightHandIndex1.is";
connectAttr "RightHandIndex1.s" "RightHandIndex2.is";
connectAttr "RightHandIndex2.s" "RightHandIndex3.is";
connectAttr "RightHandPinky.s" "RightHandPinky1.is";
connectAttr "RightHandPinky1.s" "RightHandPinky2.is";
connectAttr "RightHandPinky2.s" "RightHandPinky3.is";
connectAttr "RightForeArmRoll.s" "RightWristExtra.is";
connectAttr "RightForeArm.s" "RightForeArmExtra.is";
connectAttr "RightArmRoll.s" "RightElbowExtra.is";
connectAttr "Pelvis.s" "RightHipExtra.is";
connectAttr "Pelvis.s" "LeftHipExtra.is";
// End of dayz_skeleton.ma
